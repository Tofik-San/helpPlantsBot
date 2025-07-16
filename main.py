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

@app.on_event("startup")
async def startup():
    try:
        await application.initialize()
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"✅ Webhook установлен: {WEBHOOK_URL}")
    except Exception as e:
        logger.exception("❌ Ошибка при установке webhook")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"📥 Update: {data}")
        update = Update.de_json(data, application.bot)

        if update.message:
            chat_id = update.message.chat.id
            text = update.message.text or ""

            if text.strip() == "/start":
                await application.bot.send_message(
                    chat_id=chat_id,
                    text="🌿 Привет! Я helpPlantsBot — бот по уходу за растениями.\n\n"
                         "📸 Пришли фото растения, и я подскажу, что это и как за ним ухаживать."
                )
                return {"ok": True}

            if update.message.photo:
                file_id = update.message.photo[-1].file_id
                file = await application.bot.get_file(file_id)

                os.makedirs("temp", exist_ok=True)
                photo_path = f"temp/{file_id}.jpg"
                file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"

                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(file_url) as resp:
                            if resp.status == 200:
                                with open(photo_path, 'wb') as f:
                                    f.write(await resp.read())
                            else:
                                await application.bot.send_message(chat_id=chat_id, text="❌ Не удалось загрузить фото.")
                                return {"ok": False}
                except Exception as e:
                    logger.exception("Ошибка загрузки фото")
                    await application.bot.send_message(chat_id=chat_id, text="⚠️ Ошибка при загрузке изображения.")
                    return {"ok": False}

                await application.bot.send_message(chat_id=chat_id, text="🔍 Распознаю растение...")

                try:
                    result = await identify_plant(photo_path)
                    os.remove(photo_path)
                except Exception as e:
                    logger.exception("Ошибка в identify_plant()")
                    await application.bot.send_message(chat_id=chat_id, text="❌ Ошибка при распознавании.")
                    return {"ok": False}

                if "error" in result:
                    await application.bot.send_message(chat_id=chat_id, text="⚠️ Не удалось определить растение.")
                elif result["probability"] < 85:
                    await application.bot.send_message(chat_id=chat_id, text="🤷 Не удалось точно определить растение.")
                else:
                    name = result.get("common_names", [result["latin_name"]])[0]
                    await application.bot.send_message(
                        chat_id=chat_id,
                        text=f"🌿 Похоже, это: <b>{name}</b>\nУверенность: {result['probability']}%",
                        parse_mode="HTML"
                    )
            else:
                await application.bot.send_message(chat_id=chat_id, text="📸 Пришли фото растения.")
        return {"ok": True}

    except Exception as e:
        logger.exception("❌ Общая ошибка в webhook")
        return {"ok": False}
