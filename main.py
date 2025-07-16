import logging
import traceback
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler

import os

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
application = Application.builder().token(TOKEN).build()

# Хендлер команды /start
async def start(update: Update, context):
    await update.message.reply_text("Привет! Я бот по уходу за растениями 🌿")

application.add_handler(CommandHandler("start", start))

@app.on_event("startup")
async def startup():
    logger.info("Setting webhook...")
    await application.bot.set_webhook(WEBHOOK_URL)
    logger.info("Webhook set successfully.")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()

        if not application.ready:
            await application.initialize()

        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return {"ok": True}

    except Exception as e:
        logger.error(f"[webhook] Error processing update\n\n{traceback.format_exc()}")
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
