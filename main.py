import os
import json
import logging
from fastapi import FastAPI, Request
from telegram import Bot
from service import get_plant_data, format_plant_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)

app = FastAPI()


@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"📩 Получен запрос: {data}")

        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()

        if not text or not chat_id:
            return {"status": "ignored"}

        logger.info(f"🗣 Пользователь: {chat_id} → {text}")

        plant = get_plant_data(text)

        if plant:
            reply = format_plant_info(plant)

            image_path = f"images/{plant.get('image')}"
            if plant.get("image") and os.path.exists(image_path):
                with open(image_path, "rb") as image:
                    bot.send_photo(chat_id=chat_id, photo=image, caption=reply, parse_mode="HTML")
            else:
                bot.send_message(chat_id=chat_id, text=reply, parse_mode="HTML")
        else:
            bot.send_message(chat_id=chat_id, text="❗ Растение не найдено. Попробуйте другое название.")
    except Exception as e:
        logger.error("❌ Ошибка в обработке сообщения", exc_info=e)

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
