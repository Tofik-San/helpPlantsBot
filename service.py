import os
import logging
import aiohttp

PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")
logger = logging.getLogger(__name__)

HEADERS = {
    "Content-Type": "application/json",
    "Api-Key": PLANT_ID_API_KEY
}


async def identify_plant(image_path: str) -> dict:
    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
    except Exception as e:
        logger.error(f"[identify_plant] Ошибка при чтении файла {image_path}: {e}")
        return {"error": f"Ошибка при чтении файла: {str(e)}"}

    url = "https://api.plant.id/v2/identify"
    payload = {
        "images": [image_data.decode("latin1")],
        "modifiers": ["similar_images"],
        "plant_language": "ru",
        "plant_details": ["common_names", "url", "name_authority", "wiki_description", "taxonomy"]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=HEADERS, json=payload) as resp:
                if resp.status != 200:
                    logger.error(f"[identify_plant] API ответ {resp.status}: {await resp.text()}")
                    return {"error": f"Plant.id API ответ {resp.status}"}
                return await resp.json()
    except Exception as e:
        logger.error(f"[identify_plant] Ошибка запроса к Plant.id: {e}")
        return {"error": f"Ошибка Plant.id: {str(e)}"}
