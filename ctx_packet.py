def make_ctx(latin: str, intent: str = "general", lang: str = "ru", outlen: str = "short") -> dict:
    """
    Формирует CTX-пакет для генерации карточки ухода.
    """
    return {
        "ROLE": "botanist/pro",               # Профессиональный ботаник
        "SCOPE": "indoor_plants.care",        # Уход за комнатными растениями
        "PLANT": latin,                       # Латинское название растения
        "LANG": lang,                         # Язык ответа
        "FORMAT": "html.card.v1",              # Формат карточки
        "INTENT": intent,                      # Цель (general / watering / light и т.д.)
        "SOURCE": "RAG",                       # Источник — retrieval по базе
        "OUTLEN": outlen,                      # Краткость (short/long)
        "STRICT": "facts_only",                # Только факты из переданных данных
        "SCHEMA": "card.v1",                   # Строгая схема JSON
        "NOTES": "facts may be in Russian, English or Latin; translate to LANG"  # Добавляем ремарку про перевод
    }
