import os
import logging
from fastapi import FastAPI, Request
from telegram import Bot, Update
from dotenv import load_dotenv
from service import get_plant_data, format_plant_info

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TOKEN)
app = FastAPI()


@app.on_event("startup")
async def startup():
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        result = await bot.set_webhook(webhook_url)
        logging.info(f"✅ Webhook установлен: {result} → {webhook_url}")
    else:
        logging.warning("⚠️ Переменная WEBHOOK_URL не задана.")


@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    logging.info(f"📩 Получен запрос: {data}")

    update = Update.de_json(data, bot)

    if not update.message or not update.message.text:
        logging.info("📭 Нет текстового сообщения.")
        return {"ok": True}

    text = update.message.text
    chat_id = update.message.chat.id
    logging.info(f"🗣 Пользователь: {chat_id} → {text}")

    plant = get_plant_data(text)

    if plant:
        reply = format_plant_info(plant)
        image = plant.get("image")

        if image:
            logging.info("🖼 Отправка карточки с фото.")
            bot.send_photo(chat_id=chat_id, photo=image, caption=reply, parse_mode="HTML")
        else:
            logging.info("📨 Отправка карточки без фото.")
            bot.send_message(chat_id=chat_id, text=reply, parse_mode="HTML")
    else:
        logging.info("❌ Растение не найдено.")
        bot.send_message(chat_id=chat_id, text="❌ Растение не найдено.")

    return {"ok": True}
