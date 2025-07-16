from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import (
    Bot,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
import logging
import os

from service import (
    get_plant_data,
    get_bot_info,
    format_plant_info_base,
    format_plant_info_extended,
    identify_plant
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = FastAPI()

def get_keyboard():
    keyboard = [
        [KeyboardButton("❓ Help")],
        [KeyboardButton("📢 Канал"), KeyboardButton("ℹ️ О проекте")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def start(update):
    bot.send_message(
        chat_id=update.message.chat.id,
        text="🌿 BOTanik готов к работе. Отправь фото растения или выбери действие кнопками ниже.",
        reply_markup=get_keyboard()
    )

def handle_buttons(update):
    text = update.message.text.strip()
    if text == "/start":
        start(update)
    elif text == "ℹ️ О проекте":
        bot.send_message(
            chat_id=update.message.chat.id,
            text="🔎 Бот для распознавания растений и выдачи карточек ухода.\n\n📷 Просто отправь фото растения — бот определит его и покажет, как ухаживать.",
            reply_markup=get_keyboard()
        )
    elif text == "📢 Канал":
        bot.send_message(
            chat_id=update.message.chat.id,
            text="https://t.me/BOTanikPlants",
            reply_markup=get_keyboard()
        )
    elif text == "❓ Help":
        bot.send_message(
            chat_id=update.message.chat.id,
            text="📷 Отправь фото растения.\n🧠 Мы распознаем его и покажем, как ухаживать.\n\nЕсли бот не распознал — попробуй другое фото.",
            reply_markup=get_keyboard()
        )

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)

    if update.message and update.message.photo:
        file_id = update.message.photo[-1].file_id
        file = bot.get_file(file_id)  # исправлено: убран await

        if not os.path.exists("temp"):
            os.makedirs("temp")

        photo_path = f"temp/{file_id}.jpg"
        file.download(photo_path)  # исправлено: убран await

        await bot.send_message(
            chat_id=update.message.chat.id,
            text="🔄 Обрабатываю фото..."
        )

        result = await identify_plant(photo_path)
        if "error" in result:
            await bot.send_message(
                chat_id=update.message.chat.id,
                text="🚫 Не удалось определить растение. Попробуйте другое фото."
            )
            return JSONResponse(content={"status": "plant_id_error"})

        latin_name = result["latin_name"]
        probability = result["probability"]

        await bot.send_message(
            chat_id=update.message.chat.id,
            text=f"🌿 Похоже, это <b>{latin_name}</b>\n(уверенность: {probability}%)",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Уход", callback_data=f"care_{latin_name}")]
            ])
        )
        return JSONResponse(content={"status": "plant_identified"})

    if update.message:
        handle_buttons(update)

    elif update.callback_query:
        data = update.callback_query.data
        if data.startswith("care_"):
            latin = data.split("_", 1)[1]
            plant_list = get_plant_data(name=latin)
            if plant_list:
                plant = plant_list[0]
                msg = format_plant_info_base(plant) + "\n\n" + format_plant_info_extended(plant)
                await bot.send_message(
                    chat_id=update.callback_query.message.chat.id,
                    text=msg,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=update.callback_query.message.chat.id,
                    text="❌ Нет информации о таком растении."
                )

    return JSONResponse(content={"status": "ok"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
