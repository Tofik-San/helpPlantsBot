import json

with open("plants.json", encoding="utf-8") as f:
    PLANTS = json.load(f)

def get_plant_data(query: str) -> dict | None:
    query = query.lower()
    for plant in PLANTS:
        if query in plant["name"].lower():
            return plant
    return None

def format_plant_info(plant):
    care = plant.get("care", {})
    pest_control = "\n".join(f"• {item}" for item in plant.get("pest_control", [])) or "-"
    fertilizers = "\n".join(f"• {item}" for item in plant.get("fertilizers", [])) or "-"

    return (
        f"<b>{plant.get('name', 'Неизвестное растение')}</b>\n"
        f"Тип: {plant.get('type', '-')}\n"
        f"Климат: {plant.get('climate', '-')}\n\n"
        f"🌱 Период роста: {plant.get('growth_period', '-')}\n"
        f"⚡️ Скорость роста: {plant.get('growth_rate', '-')}\n"
        f"💛 Сочетается с: {plant.get('compatible_with', '-')}\n"
        f"🌿 Сорта: {plant.get('varieties', '-')}\n"
        f"☀️ Свет: {care.get('light', '-')}\n"
        f"💧 Полив: {care.get('watering', '-')}\n"
        f"🌱 Почва: {care.get('soil', '-')}\n"
        f"✂️ Обрезка: {care.get('pruning', '-')}\n\n"
        f"🪲 Защита от вредителей:\n{pest_control}\n\n"
        f"🧪 Удобрения:\n{fertilizers}\n\n"
        f"🪴 Горшок и корни: {plant.get('pot_and_roots', '-')}\n"
        f"📌 Использование: {plant.get('usage', '-')}\n"
        f"💡 Интересный факт: {plant.get('interesting_fact', '-')}"
    )
