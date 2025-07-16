import os
import logging
import traceback
import base64
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)
import httpx

# --- Конфиги
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")

# --- Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Telegram + FastAPI
app = FastAPI()
application = Application.builder().token(TOKEN).build()
app_state_ready = False

os.makedirs("temp", exist_ok=True)

# --- /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот по уходу за растениями 🌿")

# --- Обработка фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        temp_path = "temp/plant.jpg"
        await file.download_to_drive(custom_path=temp_path)

        await update.message.reply_text("Распознаю растение…")

        with open(temp_path, "rb") as image_file:
            image_bytes = image_file.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.plant.id/v2/identify",
                headers={"Api-Key": PLANT_ID_API_KEY},
                json={
                    "images": [image_b64],
                    "organs": ["leaf", "flower"]
                }
            )

        result = response.json()
        suggestions = result.get("suggestions", [])
        if not suggestions:
            await update.message.reply_text("Не удалось распознать растение.")
            return

        top = suggestions[0]
        name = top.get("plant_name", "неизвестно")
        prob = round(top.get("probability", 0) * 100, 2)
        await update.message.reply_text(f"🌱 Похоже, это: {name} ({prob}%)")

    except Exception as e:
        logger.error(f"[handle_photo] Ошибка: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("Ошибка при распознавании растения.")

# --- Хендлеры
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# --- Инициализация
@app.on_event("startup")
async def startup():
    global app_state_ready
    try:
        await application.initialize()
        app_state_ready = True
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info("Webhook установлен.")
    except Exception as e:
        logger.error(f"[startup] Ошибка при инициализации: {e}\n{traceback.format_exc()}")

# --- Webhook
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        if not app_state_ready:
            logger.warning("Приложение не готово.")
            return {"ok": False, "error": "Not initialized"}
        await application.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"[webhook] Ошибка: {e}\n{traceback.format_exc()}")
        return {"ok": False, "error": str(e)}

# --- Запуск
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
