import logging
import httpx
import os
import openai

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")


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


async def generate_card_with_gpt(latin_name: str, snippets: list[str]) -> str:
    logging.info(f"[GPT] Генерация карточки для: {latin_name}")
    source_text = "\n".join(snippets).strip()

    prompt = f"""Ты — ботаник-эксперт.

Вот выдержки из русских сайтов по запросу "{latin_name}":

{source_text}

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
– Формат подходит для Telegram (без markdown, emoji и HTML).
– Если данных по какому-либо пункту нет — просто пропусти его.

📌 Названия:
Интерпретируй латинское название по ботаническому словарю.
– Если есть официальное русское имя — используй его.
– Если нет — оставь только латинское.
– Не транслитерируй, не переводи дословно, не сочиняй.

Примеры:
• Ficus elastica → Резиновое дерево (Ficus elastica)
• Euonymus alatus → Бересклет крылатый (Euonymus alatus)
• Ficus benjamina → Фикус Бенджамина (Ficus benjamina)
• Thaumatophyllum xanadu → Thaumatophyllum xanadu

🚫 Запрещено:
– Придумывать народные или обиходные названия.
– Использовать метафоры, сравнения или знаковые вариации растений.
– Например: не пиши Codiaeum с рыбкой. Убери это.
– Используй только проверенные официальные русские имена, если они есть."""

    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"[GPT] Ошибка генерации карточки: {e}")
        return "Не удалось сформировать карточку ухода."
