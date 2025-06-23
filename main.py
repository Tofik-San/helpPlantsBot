import os
import logging
import json
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from telegram import Bot

from service import get_plant_data, format_plant_info

# ─── Настройка ─────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logging.error("❌ BOT_TOKEN не найден.")
    raise RuntimeError("BOT_TOKEN отсутствует")

bot = Bot(token=TOKEN)
app = FastAPI()

# ─── Проверка доступности ─────────────────
@app.get("/")
def root():
    return {"status": "ok"}

# ─── Обработка Webhook ─────────────────────
@app.post("/webhook")
async def telegram_webhook(req: Request):
    try:
        data = await req.json()
        logging.info(f"📩 Получен запрос: {json.dumps(data, ensure_ascii=False)}")

        message = data.get("message")
        if not message:
            logging.warning("⚠️ Нет поля 'message'")
            return {"ok": True}

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()
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
    except Exception as e:
        logging.exception("❌ Ошибка в обработке сообщения")

    return {"ok": True}

# ─── Запуск локально ───────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
