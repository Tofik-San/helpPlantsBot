import os
import logging
from fastapi import FastAPI, Request
from telegram import Bot, Update
from dotenv import load_dotenv
from service import get_plant_data, format_plant_info

# Загрузка переменных
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
app = FastAPI()

logging.basicConfig(level=logging.INFO)

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    logging.info(f"📩 Получен запрос: {data}")

    update = Update.de_json(data, bot)

    if not update.message or not update.message.text:
        logging.info("📭 Нет текстового сообщения.")
        return {"ok": True}

    text = update.message.text
    chat_id = update.message.chat.id
    logging.info(f"🗣 Пользователь: {chat_id} → {text}")

    plant = get_plant_data(text)
    if plant:
        reply = format_plant_info(plant)
        image = plant.get("image")

        if image:
            bot.send_photo(chat_id=chat_id, photo=image, caption=reply, parse_mode="HTML")
        else:
            bot.send_message(chat_id=chat_id, text=reply, parse_mode="HTML")
    else:
        bot.send_message(chat_id=chat_id, text="❌ Растение не найдено.")

    return {"ok": True}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
