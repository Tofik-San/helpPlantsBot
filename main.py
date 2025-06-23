import os
import logging
import telegram
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Dispatcher, MessageHandler, Filters
from dotenv import load_dotenv

from service import get_plant_data, format_plant_info

# ──────────────── Настройки ────────────────

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Например: https://your-app.up.railway.app/webhook

bot = telegram.Bot(token=TOKEN)
app = FastAPI()
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

logging.basicConfig(level=logging.INFO)

# ──────────────── Обработка сообщений ────────────────

def handle_message(update: Update, context):
    user_text = update.message.text
    chat_id = update.message.chat_id

    plant = get_plant_data(user_text)
    if plant:
        reply = format_plant_info(plant)
        image = plant.get("image")

        if image:
            bot.send_photo(chat_id=chat_id, photo=image, caption=reply, parse_mode=telegram.ParseMode.HTML)
        else:
            bot.send_message(chat_id=chat_id, text=reply, parse_mode=telegram.ParseMode.HTML)
    else:
        bot.send_message(chat_id=chat_id, text="🔍 Растение не найдено. Попробуйте другое название.")

dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# ──────────────── Webhook от Telegram ────────────────

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return {"ok": True}

# ──────────────── Установка webhook при старте ────────────────

@app.on_event("startup")
async def set_webhook():
    if not WEBHOOK_URL:
        logging.warning("WEBHOOK_URL не задан.")
    else:
        await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
        logging.info("Webhook установлен.")
