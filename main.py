import os
import aiohttp
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application
from service import identify_plant

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = FastAPI()
application = Application.builder().token(TOKEN).build()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


async def set_webhook():
    await application.bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")


@app.on_event("startup")
async def startup():
    await set_webhook()


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)

    if update.message:
        chat_id = update.message.chat.id
        text = update.message.text

        # --- Фото распознавание ---
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            file = await application.bot.get_file(file_id)

            os.makedirs("temp", exist_ok=True)
            photo_path = f"temp/{file_id}.jpg"
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"

            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    with open(photo_path, 'wb') as f:
                        f.write(await resp.read())

            await application.bot.send_message(chat_id=chat_id, text="🛠 Обрабатываем фото...")

            result = await identify_plant(photo_path)
            os.remove(photo_path)

            if "error" in result or result["probability"] < 85:
                await application.bot.send_message(chat_id=chat_id, text="⚠️ Не удалось точно определить растение.")
            else:
                name = result["name"]
                await application.bot.send_message(chat_id=chat_id, text=f"🌿 Похоже, это: {name}")
        else:
            await application.bot.send_message(chat_id=chat_id, text="📸 Пришли, пожалуйста, фото растения.")

    return {"ok": True}
