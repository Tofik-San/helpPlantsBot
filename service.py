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
        f"<i>{plant.get('latin_name')}</i>\n"
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


# ⬇️ Новый блок: интеграция с Plant.id
import aiohttp
import base64


PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")


async def identify_plant(image_path: str) -> dict:
    from pprint import pprint

    try:
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        print(f"🛑 Ошибка чтения изображения: {e}")
        return {"error": "file_read_error"}

    url = "https://api.plant.id/v2/identify"
    headers = {"Content-Type": "application/json"}
    payload = {
        "api_key": PLANT_ID_API_KEY,
        "images": [image_data],
        "plant_language": "ru",
        "plant_details": ["common_names"]
    }

    print("➡️ Отправка запроса в Plant.id")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            print(f"⬅️ Ответ от Plant.id: {response.status}")
            if response.status != 200:
                return {"error": f"Plant.id API error: {response.status}"}
            data = await response.json()

    pprint(data)

    if "suggestions" not in data or not data["suggestions"]:
        return {"error": "No plant suggestions found"}

    top = data["suggestions"][0]
    return {
        "latin_name": top.get("plant_name"),
        "common_names": top.get("plant_details", {}).get("common_names", []),
        "probability": round(top.get("probability", 0) * 100, 2)
    }
