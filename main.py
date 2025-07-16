import os
import logging
import traceback
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Логгер
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI и Telegram Application
app = FastAPI()
application = Application.builder().token(TOKEN).build()
app_state_ready = False  # Флаг инициализации

# Хендлер команды /start
async def start(update: Update, context):
    await update.message.reply_text("Привет! Я бот по уходу за растениями 🌿")

application.add_handler(CommandHandler("start", start))

@app.on_event("startup")
async def startup():
    global app_state_ready
    try:
        await application.initialize()
        app_state_ready = True
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info("Webhook set and application initialized.")
    except Exception as e:
        logger.error(f"[startup] Failed to initialize: {e}\n{traceback.format_exc()}")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        if not app_state_ready:
            logger.warning("Application not ready at webhook call.")
            return {"ok": False, "error": "Not initialized"}
        await application.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"[webhook] Error: {e}\n{traceback.format_exc()}")
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
