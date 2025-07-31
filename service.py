import os
import logging
import aiohttp
import requests
from urllib.parse import urlparse

PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
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


# --- SerpAPI integration
def get_snippets_from_serpapi(query: str) -> list[str]:
    params = {
        "q": query,
        "engine": "google",
        "hl": "ru",
        "gl": "ru",
        "num": 10,
        "api_key": os.getenv("SERPAPI_KEY"),
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()
        return [
            result["snippet"]
            for result in data.get("organic_results", [])
            if "snippet" in result
        ]
    except Exception as e:
        logger.error(f"[SerpAPI] Ошибка: {e}")
        return []


# --- Расширение под смешанные сниппеты

RU_PLANT_SOURCES = [
    "stroy-podskazka.ru",
    "floristics.info",
    "wiki-dacha.ru",
    "rastenia.info",
    "dzengarden.ru",
    "shop.pitomnik-sochi.ru"
]

def build_ru_query(ru_name: str) -> str:
    base = f"{ru_name} уход"
    sites = " OR ".join(f"site:{s}" for s in RU_PLANT_SOURCES)
    return f"{base} {sites}"

def build_en_query(latin_name: str) -> str:
    return f"{latin_name} site:en.wikipedia.org OR site:wikipedia.org"

def filter_snippets(snippets: list[str]) -> list[str]:
    keywords = ["light", "sun", "shade", "soil", "water", "prune", "maintenance", "fertilizer", "temperature", "care", "уход", "полив", "пересадка"]
    return [s for s in snippets if any(k in s.lower() for k in keywords)]

async def get_combined_snippets(latin_name: str, ru_name: str) -> list[str]:
    q_ru = build_ru_query(ru_name)
    q_en = build_en_query(latin_name)

    snippets_ru = get_snippets_from_serpapi(q_ru)
    snippets_en = get_snippets_from_serpapi(q_en)

    clean_ru = filter_snippets(snippets_ru)
    clean_en = filter_snippets(snippets_en)

    return clean_ru + clean_en

PLANT_NAME_MAP = {
    "Euonymus alatus": "Бересклет крылатый",
    "Ficus elastica": "Фикус эластика",
    "Sansevieria trifasciata": "Сансевиерия трёхполосная",
    "Zamioculcas zamiifolia": "Замиокулькас",
    "Hibiscus rosa-sinensis": "Гибискус китайский",
    "Aloe vera": "Алоэ вера",
    # дополняй
}

def map_latin_to_russian(latin_name: str) -> str:
    return PLANT_NAME_MAP.get(latin_name, latin_name)
