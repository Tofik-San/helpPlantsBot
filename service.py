from sqlalchemy import create_engine, text
import os

def get_plant_data(name_filter=None, id_filter=None, category_type=None):
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)

    with engine.connect() as connection:
        if id_filter:
            query = text("SELECT * FROM plants WHERE id = :id")
            result = connection.execute(query, {"id": id_filter}).fetchone()
            return dict(result) if result else None
        elif name_filter:
            query = text("SELECT * FROM plants WHERE LOWER(name) LIKE :name")
            result = connection.execute(query, {"name": f"%{name_filter.lower()}%"}).fetchone()
            return dict(result) if result else None
        elif category_type:
            query = text("SELECT * FROM plants WHERE category_type LIKE :category")
            result = connection.execute(query, {"category": f"%{category_type}%"})
            return [dict(row) for row in result]
        else:
            query = text("SELECT * FROM plants")
            result = connection.execute(query)
            return [dict(row) for row in result]

def format_plant_info_base(plant):
    return (
        f"<b>{plant.get('name')}</b>\n"
        f"{plant.get('short_description')}"
    )

def format_plant_info_extended(plant):
    return (
        f"🌿 <b>Тип:</b> {plant.get('category_type')}\n"
        f"☀️ <b>Свет:</b> {plant.get('light')}\n"
        f"💧 <b>Полив:</b> {plant.get('watering')}\n"
        f"🌡️ <b>Температура:</b> {plant.get('temperature')}\n"
        f"🪴 <b>Почва:</b> {plant.get('soil')}\n"
        f"🌻 <b>Удобрения:</b> {plant.get('fertilizer')}\n"
        f"✂️ <b>Уход:</b> {plant.get('care_tip')}"
    )

def get_bot_info():
    return (
        "🌿 <b>Бот по растениям</b>\n"
        "Введите название растения или выберите категорию для получения подробной информации."
    )
