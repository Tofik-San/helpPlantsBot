import os
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from service import identify_plant

# Логгер
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Инициализация
app = FastAPI()
application = Application.builder().token(TOKEN).build()

# Хэндлер
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот. Отправь фото растения — я подскажу, что это.")

application.add_handler(CommandHandler("start", start))

@app.on_event("startup")
async def on_startup():
    try:
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"[startup] Failed to set webhook: {e}")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"[webhook] Error processing update: {e}")
        return {"ok": False, "error": str(e)}
