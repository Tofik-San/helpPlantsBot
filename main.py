import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Bot, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from service import get_plant_data, format_plant_info_base, format_plant_info_extended
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = FastAPI()

info_keyboard = InlineKeyboardMarkup(
    [[InlineKeyboardButton("ℹ️ Подробнее", callback_data="more_info")]]
)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"📩 Получен запрос: {data}")

        message = data.get("message")
        callback_query = data.get("callback_query")

        if message:
            chat_id = message["chat"]["id"]
            text = message.get("text", "").strip()
            logger.info(f"🗣 Пользователь: {chat_id} → {text}")

            plant = get_plant_data(text)
            if plant:
                image_path = os.path.join("images", plant["image"])
                with open(image_path, "rb") as image:
                    reply = format_plant_info_base(plant)
                    bot.send_photo(chat_id=chat_id, photo=image, caption=reply, parse_mode="HTML", reply_markup=info_keyboard)
            else:
                bot.send_message(chat_id=chat_id, text="🔍 Растение не найдено. Попробуйте другое название.")

        elif callback_query:
            chat_id = callback_query["message"]["chat"]["id"]
            message_id = callback_query["message"]["message_id"]
            data = callback_query.get("data")

            if data == "more_info":
                text = callback_query["message"]["caption"].split("\n")[0].replace("<b>", "").replace("</b>", "").strip()
                plant = get_plant_data(text)
                if plant:
                    extended_info = format_plant_info_extended(plant)
                    bot.send_message(chat_id=chat_id, text=extended_info, parse_mode="HTML")

        return JSONResponse(content={"status": "ok"})

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}", exc_info=True)
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
