# service.py
import os
import json
import base64
import logging
import aiohttp
from urllib.parse import urlparse

# --- Логи
logger = logging.getLogger(__name__)

# --- Ключи и заголовки внешних API
PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")
HEADERS = {
    "Content-Type": "application/json",
    "Api-Key": PLANT_ID_API_KEY
}

# --- OpenAI / CTX / Retrieval / Render
from openai import AsyncOpenAI
from ctx_packet import make_ctx
from faiss_search import get_chunks_by_latin_name  # filter_by_intent не нужен
from card_formatter import render_html
from schemas import Card

# --- Константы пайплайна
K = 12
FACTS_USED = 6
CLIP = 450
TEMP = 0.0  # жёсткий детерминизм и экстрактивность
MODEL = os.getenv("MODEL", "gpt-4o-mini")
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
#   Plant.id
# =========================
async def identify_plant(image_path: str) -> dict:
    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
    except Exception as e:
        logger.error(f"[identify_plant] Ошибка при чтении файла {image_path}: {e}")
        return {"error": f"Ошибка при чтении файла: {str(e)}"}

    # ВАЖНО: Plant.id принимает base64-строки, не raw-байты/latin1
    image_b64 = base64.b64encode(image_data).decode("ascii")

    url = "https://api.plant.id/v2/identify"
    payload = {
        "images": [image_b64],
        "modifiers": ["similar_images"],
        "plant_language": "ru",
        "plant_details": ["common_names", "url", "name_authority", "wiki_description", "taxonomy"]
    }

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=HEADERS, json=payload) as resp:
                body = await resp.text()
                ct = resp.headers.get("content-type", "")
                if resp.status != 200:
                    logger.error(f"[identify_plant] status={resp.status} ct={ct} body[:200]={body[:200]}")
                    # частые коды: 401/403 (ключ), 402 (квота), 429 (rate limit)
                    return {"error": f"Plant.id API {resp.status}", "body": body[:200]}
                if "application/json" not in ct:
                    logger.error(f"[identify_plant] Non-JSON response ct={ct} body[:200]={body[:200]}")
                    return {"error": "Plant.id non-json", "body": body[:200]}
                return json.loads(body)
    except Exception as e:
        logger.error(f"[identify_plant] Ошибка запроса к Plant.id: {e}")
        return {"error": f"Ошибка Plant.id: {str(e)}"}

# =========================
#   PostgreSQL (asyncpg)
# =========================
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")
parsed = urlparse(DATABASE_URL) if DATABASE_URL else None

PG_USER = parsed.username if parsed else None
PG_PASSWORD = parsed.password if parsed else None
PG_HOST = parsed.hostname if parsed else None
PG_PORT = parsed.port if parsed else None
PG_DB = parsed.path[1:] if parsed and parsed.path.startswith('/') else None

_pool = None

async def get_pool():
    """Возвращает кэшированный пул соединений asyncpg."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            database=PG_DB,
        )
    return _pool

# --- Legacy совместимость (не используется CTX-пайплайном)
async def get_card_by_latin_name(latin_name: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT latin_name, text FROM gpt_cards WHERE latin_name=$1",
            latin_name,
        )
        return dict(row) if row else None

async def save_card(data: dict):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
        INSERT INTO gpt_cards (latin_name, text)
        VALUES ($1, $2)
        ON CONFLICT (latin_name) DO UPDATE
        SET text = EXCLUDED.text
        """
        await conn.execute(query, data.get("latin_name"), data.get("text"))

# --- Кэш по (latin_name, intent) и html
async def get_card_by_latin_intent(latin_name: str, intent: str = "general") -> str | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT html FROM gpt_cards WHERE latin_name=$1 AND intent=$2",
            latin_name, intent
        )
        return row["html"] if row else None

async def save_card_html(latin_name: str, intent: str, html: str, source: str = "RAG"):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO gpt_cards (latin_name, intent, html, source)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (latin_name, intent)
            DO UPDATE SET html = EXCLUDED.html, source = EXCLUDED.source
        """, latin_name, intent, html, source)

# =========================
#   Маппинг имён (оставляем)
# =========================
PLANT_NAME_MAP = {
    "Euonymus alatus": "Бересклет крылатый",
    "Ficus elastica": "Фикус эластика",
    "Sanseveria trifasciata": "Сансевиерия трёхполосная",
    "Zamioculcas zamiifolia": "Замиокулькас",
    "Hibiscus rosa-sinensis": "Гибискус китайский",
    "Aloe vera": "Алоэ вера",
    # дополняй
}

def map_latin_to_russian(latin_name: str) -> str:
    return PLANT_NAME_MAP.get(latin_name, latin_name)

# =========================
#   CTX-карточка (FAISS → GPT(JSON) → HTML → Cache)
# =========================
async def generate_card(latin_name: str, intent: str = "general", lang: str = "ru", outlen: str = "short") -> str:
    # 1) Кэш
    cached = await get_card_by_latin_intent(latin_name, intent)
    if cached:
        logger.info(f"[CACHE] hit latin={latin_name} intent={intent}")
        return cached

    # 2) Retrieval (intent прокидываем внутрь; для general — None)
    intent_for_rag = None if intent == "general" else intent
    chunks = get_chunks_by_latin_name(latin_name, top_k=K, intent=intent_for_rag)
    facts = [c["text"][:CLIP] for c in chunks][:FACTS_USED]

    if not facts:
        logger.warning(f"[RAG] No facts latin={latin_name}")
        # Без HTML-тегов — чтобы Telegram не ругался
        return "Недостаточно данных"

    # 3) CTX + строгий формат (экстрактивность) — нумеруем факты
    numbered = [f"[{i+1}] {t}" for i, t in enumerate(facts)]
    ctx = make_ctx(latin_name, intent, lang, outlen)
    sys_msg = (
        "You are an extractive writer. Use ONLY the provided FACTS. "
        "Do not add or infer anything that is not explicitly in FACTS. "
        "If a field cannot be filled strictly from FACTS, keep it short. "
        "Keep original wording, prefer verbatim. "
        "For each paragraph in blocks and each tip, append space+'[n]' "
        "with the most relevant FACT index. "
        "Return a single valid JSON object for schema card.v1. No extra text."
    )
    usr_msg = json.dumps(
        {"CTX": ctx, "SCHEMA": Card.model_json_schema(), "FACTS": numbered},
        ensure_ascii=False
    )

    # 4) GPT(JSON)
    rsp = await client.chat.completions.create(
        model=MODEL,
        temperature=TEMP,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": usr_msg}
        ]
    )

    # 5) Валидация JSON → HTML
    card = Card.model_validate_json(rsp.choices[0].message.content)
    html = render_html(card)

    # 6) Кэш + метрики
    await save_card_html(latin_name, intent, html, source="RAG")

    usage = getattr(rsp, "usage", None)
    try:
        if usage:
            logger.info(
                f"[METRICS] prompt={usage.prompt_tokens} "
                f"completion={usage.completion_tokens} total={usage.total_tokens}"
            )
    except Exception:
        pass

    return html
