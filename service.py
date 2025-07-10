from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def get_plant_data(query: str, by_id=False) -> dict | None:
    with engine.connect() as conn:
        if by_id:
            stmt = text("SELECT * FROM plants WHERE id = :id")
            result = conn.execute(stmt, {"id": int(query)}).mappings().first()
        else:
            stmt = text("SELECT * FROM plants WHERE LOWER(name) LIKE :name")
            result = conn.execute(stmt, {"name": f"%{query.lower()}%"}).mappings().first()
        return dict(result) if result else None

def format_plant_info_base(plant):
    return (
        f"<b>{plant.get('name')}</b>\n"
        f"{plant.get('short_description')}\n\n"
        f"🌿 <b>Тип:</b> {plant.get('category_type')}\n"
        f"☀️ <b>Свет:</b> {plant.get('light')}\n"
        f"💧 <b>Полив:</b> {plant.get('watering')}\n"
        f"🌡️ <b>Температура:</b> {plant.get('temperature')}\n"
        f"🪴 <b>Почва:</b> {plant.get('soil')}\n"
        f"🌻 <b>Удобрения:</b> {plant.get('fertilizer')}\n"
        f"✂️ <b>Уход:</b> {plant.get('care_tip')}"
    )

def format_plant_info_extended(plant):
    insights = plant.get("insights")
    if insights:
        return f"<b>📄 Подробная статья по {plant.get('name')}</b>\n\n{insights}"
    else:
        return "Для этого растения пока нет расширенной статьи."

def get_bot_info() -> str:
    return (
        "🌱 Отправь название растения, чтобы получить карточку ухода и подробную статью.\n"
        "📸 Бот показывает фото, советы по поливу, освещению и уходу.\n"
        "👨‍🌾 Подходит для дома, питомников, магазинов.\n\n"
        "🚀 Работает на Python, FastAPI, PostgreSQL и Telegram Bot API.\n"
        "Связь: @veryhappyEpta"
    )
