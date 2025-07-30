async def generate_care_card(latin_name: str) -> str:
    from loguru import logger

    # 1. Проверка кэша
    data = await get_card_by_latin_name(latin_name)
    if data:
        return f"<pre>{html.escape(data.get('text', '')[:3000])}</pre>"

    # 2. Поиск чанков в FAISS
    raw_chunks = get_chunks_by_latin_name(latin_name, top_k=10)
    chunks = [ch for ch in raw_chunks if latin_name.lower() in ch["latin_name"].lower()]
    if not chunks:
        chunks = raw_chunks[:5]  # fallback хотя бы что-то

    logger.debug(f"[generate_care_card] Чанков найдено: {len(chunks)}")

    if not chunks:
        return f"❌ Не найдено информации по: {latin_name}"

    # 3. Промт
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

    # 4. GPT-запрос
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

    # 5. Сохранение
    await save_card({
        "latin_name": latin_name,
        "text": gpt_raw
    })

    return f"<pre>{html.escape(gpt_raw[:3000])}</pre>"
