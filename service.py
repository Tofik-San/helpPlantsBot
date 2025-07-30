async def generate_care_card(latin_name: str) -> str:
    import html
    import json
    from pathlib import Path
    from loguru import logger

    from faiss_search import get_chunks_by_latin_name
    from .db import get_card_by_latin_name, save_card

    # 1. Проверка кэша
    data = await get_card_by_latin_name(latin_name)
    if data:
        return f"<pre>{html.escape(data.get('text', '')[:3000])}</pre>"

    # 2. Загрузка мапа латинских имён
    LATIN_MAP_PATH = Path("latin_name_map.json")
    latin_name_map = json.loads(LATIN_MAP_PATH.read_text(encoding="utf-8"))

    def resolve_latin_name(query: str) -> str:
        query = query.lower()
        for fname, canon in latin_name_map.items():
            canon_l = canon.lower()
            if query in canon_l or canon_l in query:
                return canon
        return query

    latin_query = resolve_latin_name(latin_name)

    # 3. Поиск чанков
    raw_chunks = get_chunks_by_latin_name(latin_query, top_k=10)
    chunks = [ch for ch in raw_chunks if latin_query.lower() in ch["latin_name"].lower()]
    if not chunks:
        chunks = raw_chunks[:5]

    logger.debug(f"[generate_care_card] Чанков найдено: {len(chunks)}")

    if not chunks:
        return f"❌ Не найдено информации по: {latin_name}"

    # 4. Промт
    prompt_text = f"""Ты — специалист по уходу за растениями.
Составь структурированную карточку ухода на основе текста ниже.

Название растения: {latin_name}

Фрагменты:
{chr(10).join(f'- {ch["content"]}' for ch in chunks)}

Собери карточку для Telegram. Без источников. Без воды. Структурируй по смыслу:
🌿 Название:
{latin_name}

🧬 Семейство:
...

📂 Категория:
...

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
- Если блока нет — пиши: "Информация отсутствует."
- Не меняй порядок блоков.
- Эмодзи — только в заголовках.
- Без вводных ("рекомендуется", "следует", "важно").
"""

    # 5. GPT
    try:
        completion = await openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=1500,
            temperature=0.3
        )
        gpt_raw = completion.choices[0].message.content.strip()
        gpt_raw = gpt_raw.replace("**", "").replace("__", "")
    except Exception as e:
        logger.error(f"[generate_care_card] GPT ошибка: {e}")
        return f"<b>Ошибка генерации:</b>\n\n<pre>{html.escape(str(e))}</pre>"

    # 6. Сохранение
    await save_card({
        "latin_name": latin_name,
        "text": gpt_raw
    })

    return f"<pre>{html.escape(gpt_raw[:3000])}</pre>"
import requests
import base64
import os
from loguru import logger

async def identify_plant(photo_path: str) -> str | None:
    """Определение растения по фото через Plant.id"""
    url = "https://api.plant.id/v2/identify"
    api_key = os.getenv("PLANT_ID_API_KEY")

    with open(photo_path, "rb") as f:
        image_bytes = f.read()

    headers = {"Content-Type": "application/json"}
    payload = {
        "images": [f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode()}"],
        "organs": ["leaf", "flower", "fruit", "bark"],
        "similar_images": False
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20, auth=(api_key, ""))
        result = response.json()

        suggestions = result.get("suggestions", [])
        if not suggestions:
            return None

        best = suggestions[0]
        plant_name = best.get("plant_name", "")
        return plant_name
    except Exception as e:
        logger.error(f"[identify_plant] Ошибка: {e}")
        return None
