import os
import aiohttp
import logging
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, Defaults
from service import identify_plant

# Инициализация
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
defaults = Defaults(parse_mode="HTML")
application = Application.builder().token(TOKEN).defaults(defaults).build()

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен: {WEBHOOK_URL}")


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    print("📩 UPDATE:", data)

    update = Update.de_json(data, bot)

    if update.message:
        chat_id = update.message.chat_id

        # 📌 Обработка команды /start
        if update.message.text and update.message.text.startswith("/start"):
            await bot.send_message(
                chat_id=chat_id,
                text="🌱 Привет! Я бот по уходу за растениями. Отправь фото растения — я подскажу, что это и как ухаживать.",
            )
            return {"ok": True}

        # 📷 Обработка фото
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            file = await bot.get_file(file_id)
            file_path = f"temp/{file_id}.jpg"
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"

            os.makedirs("temp", exist_ok=True)

            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    with open(file_path, 'wb') as f:
                        f.write(await resp.read())

            await bot.send_message(chat_id=chat_id, text="🧠 Обрабатываю фото...")

            result = await identify_plant(photo_path=file_path)
            os.remove(file_path)

            if "error" in result or result.get("probability", 100) < 85:
                await bot.send_message(chat_id=chat_id, text="😔 Не удалось точно определить растение.")
            else:
                name = result["name"]
                prob = result["probability"]
                await bot.send_message(chat_id=chat_id, text=f"🌿 Похоже, это <b>{name}</b> (уверенность: {prob}%)")

        else:
            await bot.send_message(chat_id=chat_id, text="⚠️ Отправь фото растения или команду /start")

    return {"ok": True}
