import json

with open("plants.json", encoding="utf-8") as f:
    PLANTS = json.load(f)

def get_plant_data(query: str) -> dict | None:
    query = query.lower()
    for plant in PLANTS:
        if query in plant["name"].lower():
            return plant
    return None

def format_plant_info_base(plant):
    return (
        f"<b>{plant.get('name')}</b>\n"
        f"Тип: {plant.get('type')}\n"
        f"Климат: {plant.get('climate')}\n\n"
        f"🌱 Период роста: {plant.get('growth_period')}\n"
        f"⚡️ Скорость роста: {plant.get('growth_rate')}"
    )

def format_plant_info_extended(plant):
    care = plant.get("care", {})
    pest_control = "\n".join(f"• {item}" for item in plant.get("pest_control", []))
    fertilizers = "\n".join(f"• {item}" for item in plant.get("fertilizers", []))

    return (
        f"❤️ Сочетается с: {plant.get('compatible_with')}\n"
        f"🌿 Сорта: {plant.get('varieties')}\n"
        f"☀️ Свет: {care.get('light')}\n"
        f"💧 Полив: {care.get('watering')}\n"
        f"🌱 Почва: {care.get('soil')}\n"
        f"✂️ Обрезка: {care.get('pruning')}\n\n"
        f"🛡️ Защита от вредителей:\n{pest_control}\n\n"
        f"🌻 Удобрения:\n{fertilizers}\n\n"
        f"🪴 Горшки и корни: {plant.get('pot_and_roots')}\n"
        f"✅ Использование: {plant.get('usage')}\n\n"
        f"📌 Интересный факт: {plant.get('interesting_fact')}"
    )

def get_bot_info() -> str:
    return (
        "🌱 Тыкаешь в фотки, гадаешь по листьям? Хватит. Просто напиши название — бот покажет всё:\n\n"
        "• как поливать, когда обрезать\n"
        "• где сажать, как не угробить\n"
        "• фото, лайфхаки, интересные факты\n\n"
        "⚡ Быстро. Без тупых форм, рекламы и логинов.\n"
        "Один бот — весь каталог у тебя в чате.\n\n"
        "🧠 В разработке:\n"
        "• подбор растений под интерьер и климат\n"
        "• экспорт в Excel и PDF\n"
        "• кастомизация под бренд, сайт или соцсеть\n"
        "• подписка для питомников и магазинов\n\n"
        "🏪 У вас свой ассортимент?\n"
        "Бот легко адаптируется под базу магазина или питомника:\n"
        "названия, описания, цены, фото — всё можно встроить.\n\n"
        "🎯 Другая ниша?\n"
        "От растений до ремонта, от фитнеса до финтеха —\n"
        "сделаем чат-бота под любое направление или бизнес-задачу.\n\n"
        "🛠️ Используемый стек:\n"
        "Python · FastAPI · Telegram Bot API · Docker · Railway · OpenAI API · Prompt Engineering\n\n"
        "🤖 Возможна интеграция GPT‑4o —\n"
        "новейшей версии с поддержкой текста, изображений и логики.\n"
        "Может больше, отвечает умнее, обучается на ваших данных.\n\n"
        "🚀 Бот — часть большого проекта по автоматизации ухода за растениями.\n"
        "Проверяй, тестируй, делись — или заказывай своего.\n\n"
        "📩 Связь и заказ: @veryhappyEpta"
    )
