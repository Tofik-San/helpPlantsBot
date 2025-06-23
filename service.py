import json

with open("plants.json", encoding="utf-8") as f:
    PLANTS = json.load(f)

def get_plant_data(query: str) -> dict | None:
    query = query.lower()
    for plant in PLANTS:
        if query in plant["name"].lower():
            return plant
    return None

def format_plant_info(plant: dict) -> str:
    care = plant.get("care", {})
    return (
        f"<b>{plant['name']}</b>\n"
        f"📌 Тип: {plant.get('type', '-')}\n"
        f"☀️ Свет: {care.get('light', '-')}\n"
        f"💧 Полив: {care.get('watering', '-')}\n"
        f"🌱 Почва: {care.get('soil', '-')}\n"
        f"✂️ Обрезка: {care.get('pruning', '-')}\n"
        f"🌍 Климат: {plant.get('climate', '-')}\n"
        f"💡 Факт: {plant.get('facts', '-')}"
    )
