import os
import logging
import aiohttp

PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")
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

PG_HOST = os.getenv("PG_HOST")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DB = os.getenv("PG_DB")

_pool = None

async def get_pool():
    """Return a cached asyncpg connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=PG_HOST,
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
            "SELECT * FROM gpt_cards WHERE latin_name=$1",
            latin_name,
        )
        return dict(row) if row else None


async def save_card(data: dict):
    """Insert or update care card in PostgreSQL."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        fields = [
            "latin_name",
            "name",
            "short_description",
            "category_type",
            "light",
            "watering",
            "temperature",
            "soil",
            "fertilizer",
            "care_tip",
            "insights",
        ]
        values = [data.get(f) for f in fields]
        placeholders = ", ".join(f"${i}" for i in range(1, len(fields) + 1))
        update_set = ", ".join(f"{f}=EXCLUDED.{f}" for f in fields[1:])
        query = (
            f"INSERT INTO gpt_cards ({', '.join(fields)}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT(latin_name) DO UPDATE SET {update_set}"
        )
        await conn.execute(query, *values)

