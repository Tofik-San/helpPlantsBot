import os
import logging
import aiohttp
import requests
from urllib.parse import urlparse
from openai import AsyncOpenAI

PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

logger = logging.getLogger(__name__)

HEADERS = {
    "Content-Type": "application/json",
    "Api-Key": PLANT_ID_API_KEY
}


async def identify_plant(image_path: str) -> dict:
    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
    except Exception as e:
        logger.error(f"[identify_plant] Ошибка при чтении файла {image_path}: {e}")
        return {"error": f"Ошибка при чтении файла: {str(e)}"}

    url = "https://api.plant.id/v2/identify"
    payload = {
        "images": [image_data.decode("latin1")],
        "modifiers": ["similar_images"],
        "plant_language": "ru",
        "plant_details": ["common_names", "url", "name_authority", "wiki_description", "taxonomy"]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=HEADERS, json=payload) as resp:
                if resp.status != 200:
                    logger.error(f"[identify_plant] API ответ {resp.status}: {await resp.text()}")
                    return {"error": f"Plant.id API ответ {resp.status}"}
                return await resp.json()
    except Exception as e:
        logger.error(f"[identify_plant] Ошибка запроса к Plant.id: {e}")
        return {"error": f"Ошибка Plant.id: {str(e)}"}


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


# --- SerpAPI integration
def get_snippets_from_serpapi(latin_name: str) -> list[str]:
    params = {
        "engine": "google",
        "q": f"{latin_name} уход site:.ru",
        "hl": "ru",
        "num": 5,
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()

        snippets = []
        for result in data.get("organic_results", []):
            snippet = result.get("snippet")
            if snippet:
                snippets.append(snippet)

        return snippets
    except Exception as e:
        logger.error(f"[SerpAPI] Ошибка: {e}")
        return []


# --- GPT card generation
async def generate_card_with_gpt(latin_name: str, snippets: list[str]) -> str:
    prompt = f"""Ты — ботаник-эксперт.

Вот выдержки из русских сайтов по запросу "{latin_name}":

{'\n'.join(snippets)}

На основе этих данных сгенерируй лаконичную, структурированную карточку ухода.

Вывод строго по формату:
Название: [официальное русское, если есть] ({latin_name})
Свет: ...
Полив: ...
Температура: ...
Почва: ...
Удобрения: ...
Советы: ...

🔒 Правила:
– Все пункты — коротко, чётко, без лишнего текста.
– Язык — только русский.
– Стиль — технически точный, без оценок и описательной лирики.
– Формат подходит для отображения в Telegram (без markdown, emoji и HTML).
– Если данных по какому-либо пункту нет — просто пропусти его.

📌 Названия:
Интерпретируй латинское название по ботаническому словарю.
– Если есть официальное русское имя — используй его.
– Если нет — оставь только латинское.
– Не транслитерируй, не переводи дословно, не сочиняй.

🚫 Запрещено:
– Придумывать народные или обиходные названия.
– Использовать метафоры, сравнения или знаковые вариации растений.
– Например: не пиши Codiaeum с рыбкой. Убери это.
– Используй только проверенные официальные русские имена, если они есть."""

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[generate_card_with_gpt] Ошибка: {e}")
        return "❌ Ошибка генерации карточки через GPT."
