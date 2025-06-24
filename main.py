import os
import json
import logging
from fastapi import FastAPI, Request
from telegram import Bot, ReplyKeyboardMarkup
from service import get_plant_data, format_plant_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)

info_keyboard = ReplyKeyboardMarkup(
    keyboard=[["ℹ️ Инфо"]],
    resize_keyboard=True,
    one_time_keyboard=False
)

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

        if text.lower() in ["инфо", "ℹ️ инфо"]:
            bot.send_message(
                chat_id=chat_id,
                text="🌿 Этот бот помогает ухаживать за растениями.\nНапиши название растения — получишь инструкцию, фото и факты.",
                reply_markup=info_keyboard
            )
            return {"status": "ok"}

        plant = get_plant_data(text)

        if plant:
            reply = format_plant_info(plant)

            image_path = f"images/{plant.get('image')}"
            if plant.get("image") and os.path.exists(image_path):
                with open(image_path, "rb") as image:
                    bot.send_photo(chat_id=chat_id, photo=image, caption=reply, parse_mode="HTML", reply_markup=info_keyboard)
            else:
                bot.send_message(chat_id=chat_id, text=reply, parse_mode="HTML", reply_markup=info_keyboard)
        else:
            bot.send_message(chat_id=chat_id, text="❗ Растение не найдено. Попробуйте другое название.", reply_markup=info_keyboard)
    except Exception as e:
        logger.error("❌ Ошибка в обработке сообщения", exc_info=e)

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
