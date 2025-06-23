import os
import telegram
import logging
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from telegram import Update

from service import get_plant_data, format_plant_info

# Загрузка переменных
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telegram.Bot(token=TOKEN)
app = FastAPI()

logging.basicConfig(level=logging.INFO)


# 🔹 Установка webhook вручную при запуске
@app.on_event("startup")
async def startup():
    if WEBHOOK_URL:
        url = f"{WEBHOOK_URL}/webhook"
        set_hook = await bot.set_webhook(url)
        logging.info(f"Webhook установлен: {set_hook}")
    else:
        logging.warning("WEBHOOK_URL не задан.")


# 🔹 Обработка запроса от Telegram
@app.post("/webhook")
async def process_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)

    if not update.message or not update.message.text:
        return {"ok": True}

    text = update.message.text
    chat_id = update.message.chat.id
    plant = get_plant_data(text)

    if plant:
        reply = format_plant_info(plant)
        image = plant.get("image")

        if image:
            bot.send_photo(chat_id=chat_id, photo=image, caption=reply, parse_mode=telegram.ParseMode.HTML)
        else:
            bot.send_message(chat_id=chat_id, text=reply, parse_mode=telegram.ParseMode.HTML)
    else:
        bot.se
