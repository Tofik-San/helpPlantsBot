import os
import logging
import aiohttp
import requests
from urllib.parse import urlparse
import httpx
import openai

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
logger = logging.getLogger(__name__)

HEADERS = {
    "Content-Type": "application/json",
    "Api-Key": PLANT_ID_API_KEY
}


async def get_snippets_from_serpapi(latin_name: str, max_snippets: int = 10) -> list[str]:
    logging.info(f"[SerpAPI] Поиск по: {latin_name}")

    query = (
        f"{latin_name} "
        "уход OR содержание OR особенности OR советы OR лайфхаки "
        "site:.ru"
    )

    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": "ru",
        "num": 20,
    }

async def generate_card_with_gpt(latin_name: str, snippets: list[str]) -> str:
    prompt = (
        f"Ты бот, создающий карточки ухода за растениями.\n"
        f"Название (латынь): {latin_name}\n\n"
        f"Собери на основе этих данных карточку ухода:\n"
        f"{chr(10).join(snippets)}\n\n"
        f"Формат:\n"
        f"📘 Название\n"
        f"💡 Краткое описание\n"
        f"☀️ Свет\n"
        f"💧 Полив\n"
        f"🌡️ Температура\n"
        f"🪴 Почва\n"
        f"🧪 Удобрения\n"
        f"⚠️ Особенности\n"
        f"📌 Лайфхаки"
    )

    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            api_key=OPENAI_API_KEY,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=900
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"[GPT] Ошибка генерации карточки: {e}")
        return "Не удалось сформировать карточку ухода."

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

        results = data.get("organic_results", [])
        snippets = [
            item["snippet"].strip()
            for item in results
            if "snippet" in item
        ][:max_snippets]

        logging.info(f"[SerpAPI] Найдено сниппетов: {len(snippets)}")
        return snippets

    except Exception as e:
        logging.error(f"[SerpAPI] Ошибка: {e}")
        return []


# --- PostgreSQL connection pool
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
    """Return a cached asyncpg connection pool."""
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


async def get_card_by_latin_name(latin_name: str) -> dict | None:
    """Fetch care card by latin name from PostgreSQL."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT latin_name, text FROM gpt_cards WHERE latin_name=$1",
            latin_name,
        )
        return dict(row) if row else None


async def save_card(data: dict):
    """Insert or update care card in PostgreSQL."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
        INSERT INTO gpt_cards (latin_name, text)
        VALUES ($1, $2)
        ON CONFLICT (latin_name) DO UPDATE
        SET text = EXCLUDED.text
        """
        await conn.execute(query, data.get("latin_name"), data.get("text"))


