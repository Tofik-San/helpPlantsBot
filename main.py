from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application
from service import (
    get_plant_data,
    get_bot_info,
    format_plant_info_base,
    format_plant_info_extended,
    identify_plant
)
import os
import aiohttp
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = FastAPI()
application = Application.builder().token(TOKEN).build()  # PTB Application instance


def get_keyboard():
    keyboard = [
        [KeyboardButton("❓ Help")],
        [KeyboardButton("📢 Канал"), KeyboardButton("ℹ️ О проекте")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


@app.on_event("startup")
async def set_webhook():
    await application.bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")


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

            await application.bot.send_message(chat_id=chat_id, text="🔄 Обрабатываю фото...")

            result = await identify_plant(photo_path)
            os.remove(photo_path)

            if "error" in result or result["probability"] < 85:
                await application.bot.send_message(chat_id=chat_id, text="🚫 Не удалось точно определить растение. Попробуйте другое фото.")
                return JSONResponse(content={"status": "plant_id_error"})

            latin_name = result["latin_name"]
            probability = result["probability"]

            await application.bot.send_message(
                chat_id=chat_id,
                text=f"🌿 Похоже, это <b>{latin_name}</b>\nУверенность: {probability}%",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Уход", callback_data=f"care_{latin_name}")]
                ])
            )
            return JSONResponse(content={"status": "plant_identified"})

        # --- Кнопки ---
        if text:
            text = text.strip()

            if text == "/start":
                await application.bot.send_message(chat_id=chat_id, text="🌿 BOTanik готов к работе. Отправь фото растения или выбери действие кнопками ниже.", reply_markup=get_keyboard())
            elif text == "ℹ️ О проекте":
                await application.bot.send_message(chat_id=chat_id, text="🔎 Бот для распознавания растений и выдачи карточек ухода.\n\n📷 Просто отправь фото растения — бот определит его и покажет, как ухаживать.", reply_markup=get_keyboard())
            elif text == "📢 Канал":
                await application.bot.send_message(chat_id=chat_id, text="https://t.me/BOTanikPlants", reply_markup=get_keyboard())
            elif text == "❓ Help":
                await application.bot.send_message(chat_id=chat_id, text="📷 Отправь фото растения.\n🧠 Мы распознаем его и покажем, как ухаживать.\n\nЕсли бот не распознал — попробуй другое фото.", reply_markup=get_keyboard())

    elif update.callback_query:
        data = update.callback_query.data
        chat_id = update.callback_query.message.chat.id

        if data.startswith("care_"):
            latin = data.split("_", 1)[1]
            plant_list = get_plant_data(name=latin)
            if plant_list:
                plant = plant_list[0]
                msg = format_plant_info_base(plant) + "\n\n" + format_plant_info_extended(plant)
                await application.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
            else:
                await application.bot.send_message(chat_id=chat_id, text="❌ Уход пока не добавлен.\n📩 Предложите добавить!")

    return JSONResponse(content={"status": "ok"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
