import os
import logging
import aiohttp
import html
from urllib.parse import urlparse
import asyncpg
from loguru import logger
from faiss_search import get_chunks_by_latin_name
from openai import AsyncOpenAI

# --- ENV ---
PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# --- HEADERS ---
HEADERS = {
    "Content-Type": "application/json",
    "Api-Key": PLANT_ID_API_KEY
}

# --- IDENTIFY PLANT ---
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

# --- DATABASE ---
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

# --- CARD GENERATION ---
async def generate_care_card(latin_name: str) -> str:
    data = await get_card_by_latin_name(latin_name)
    if data:
        return f"<pre>{html.escape(data.get('text', '')[:3000])}</pre>"

    chunks = get_chunks_by_latin_name(latin_name)
    if not chunks:
        return f"❌ Не найдено информации по: {latin_name}"

    prompt_text = f"""Ты — специалист по уходу за растениями.
Составь структурированную карточку ухода на основе текста ниже.

Название растения: {latin_name}

Фрагменты:
{chr(10).join(f'- {s}' for s in chunks)}

Собери карточку для Telegram. Без источников. Без воды. Структурируй по смыслу:
🌿 Название:
{latin_name}

🧬 Семейство:
(уточняется из чанков)

📂 Категория:
(уточняется из чанков)

💡 Свет:
...

💧 Полив:
...

🌡 Температура:
...

💨 Влажность:
...

🍽 Удобрения:
...

🌱 Почва:
...

♻ Пересадка:
...

🧬 Размножение:
...

⭐ Особенности:
...

Правила:
- Используй только факты из фрагментов. Не выдумывай.
- Если блока нет — пиши: \"Информация отсутствует.\"
- Не меняй порядок блоков.
- Эмодзи — только в заголовках.
- Без вводных (\"рекомендуется\", \"следует\", \"важно\")."""

    completion = await openai_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt_text}],
        max_tokens=1500,
        temperature=0.3
    )

    gpt_raw = completion.choices[0].message.content.strip()
    gpt_raw = gpt_raw.replace("**", "").replace("__", "")

    await save_card({
        "latin_name": latin_name,
        "text": gpt_raw
    })

    return f"<pre>{html.escape(gpt_raw[:3000])}</pre>"
