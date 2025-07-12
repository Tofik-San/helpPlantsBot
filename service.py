from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)


def get_plant_data(name=None, category_filter=None, id_filter=None):
    with engine.connect() as connection:
        if id_filter:
            query = text("SELECT * FROM plants WHERE id = :id")
            result = connection.execute(query, {"id": id_filter}).mappings()
        elif category_filter:
            query = text("SELECT * FROM plants WHERE category_type ILIKE :category")
            result = connection.execute(query, {"category": f"%{category_filter}%"}).mappings()
        elif name:
            query = text("SELECT * FROM plants WHERE name ILIKE :name")
            result = connection.execute(query, {"name": f"%{name}%"}).mappings()
        else:
            return None

        return [format_plant(row) for row in result]


def list_varieties_by_category(category: str):
    with engine.connect() as connection:
        query = text("SELECT * FROM plants WHERE category_type ILIKE :category")
        result = connection.execute(query, {"category": f"%{category}%"}).mappings()
        return [format_plant(row) for row in result]


def format_plant(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "latin_name": row["latin_name"],
        "short_description": row["short_description"],
        "category_type": row["category_type"],
        "light": row["light"],
        "watering": row["watering"],
        "temperature": row["temperature"],
        "soil": row["soil"],
        "fertilizer": row["fertilizer"],
        "care_tip": row["care_tip"],
        "insights": row["insights"],
    }


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


def format_plant_insights(plant):
    return plant.get("insights", "").strip()


def get_bot_info():
    return (
        "🌿 Этот бот поможет тебе узнать всё о растениях.\n\n"
        "📌 Отправь название растения или выбери категорию, чтобы получить карточку с уходом, фото и советами."
    )
