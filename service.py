from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def get_plant_data(name=None, category_filter=None, id_filter=None, page_size=5, page_num=0):
    """Получаем данные о растениях с фильтрацией по категории и пагинацией"""
    with engine.connect() as connection:
        if id_filter:
            query = text("SELECT * FROM plants WHERE id = :id")
            result = connection.execute(query, {"id": id_filter}).mappings()
        elif category_filter:
            category_filter = category_filter.strip() if category_filter else None
            if category_filter:
                query = text("""
                    SELECT * FROM plants
                    WHERE category_type ILIKE :category
                    LIMIT :limit OFFSET :offset
                """)
                result = connection.execute(
                    query,
                    {"category": f"%{category_filter}%", "limit": page_size, "offset": page_size * page_num}
                ).mappings()
            else:
                return None  # Если фильтр пуст, не выполнять запрос
        elif name:
            query = text("SELECT * FROM plants WHERE name ILIKE :name")
            result = connection.execute(query, {"name": f"%{name}%"}).mappings()
        else:
            query = text("SELECT * FROM plants LIMIT :limit OFFSET :offset")
            result = connection.execute(
                query, {"limit": page_size, "offset": page_size * page_num}
            ).mappings()

        plants = []
        for row in result:
            plant = {
                "id": row["id"],
                "image": row["image"],
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
                "insights": row["insights"]
            }
            plants.append(plant)

        return plants if plants else None

def paginate_plants(plant_list, page_size=5):
    """Разбиваем список сортов на страницы с заданным количеством элементов (по 5 сортов на страницу)."""
    return [plant_list[i:i + page_size] for i in range(0, len(plant_list), page_size)]

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
        "🌿 Этот бот поможет тебе узнать всё о растениях.\n\n"
        "📌 Отправь название растения или выбери категорию, чтобы получить карточку с уходом, фото и советами."
    )
