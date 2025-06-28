import os
import logging
from fastapi import FastAPI, Request
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from service import get_plant_data, format_plant_info

TOKEN = os.environ["BOT_TOKEN"]
bot = Bot(token=TOKEN)
app = FastAPI()
logging.basicConfig(level=logging.INFO)

info_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("ℹ️ Подробнее", callback_data="more_info")]])

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    logging.info(f"📩 Получен запрос: {data}")

    message = data.get("message")
    callback_query = data.get("callback_query")

    if message:
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()
        user_name = message["from"].get("username")
        logging.info(f"🗣 Пользователь: {chat_id} ({user_name}) → {text}")

        plant = get_plant_data(text)
        if plant:
            reply_full = format_plant_info(plant)
            reply_short = reply_full[:900] + "...\nНажмите 'ℹ️ Подробнее' для подробностей."

            image_path = f"images/{plant['image']}"
            with open(image_path, "rb") as image:
                bot.send_photo(chat_id=chat_id, photo=image, caption=reply_short, parse_mode="HTML", reply_markup=info_keyboard)
        else:
            bot.send_message(chat_id=chat_id, text="❌ Растение не найдено. Попробуйте другое название.")

    elif callback_query:
        chat_id = callback_query["message"]["chat"]["id"]
        message_id = callback_query["message"]["message_id"]
        data = callback_query["data"]
        user_message = callback_query["message"]["caption"].split("\n")[0].replace("🌿 ", "")

        if data == "more_info":
            plant = get_plant_data(user_message)
            if plant:
                reply_full = format_plant_info(plant)
                bot.send_message(chat_id=chat_id, text=reply_full, parse_mode="HTML")
            else:
                bot.send_message(chat_id=chat_id, text="❌ Не удалось найти подробности по этому растению.")

    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
