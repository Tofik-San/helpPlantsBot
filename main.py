import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import (
    Bot, Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
)
from telegram.error import TelegramError
from service import get_plant_data, format_plant_info_base, format_plant_info_extended, get_bot_info
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)
app = FastAPI()

info_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("📋 Подробнее"), KeyboardButton("🛒 Заказать услугу")]],
    resize_keyboard=True,
    one_time_keyboard=False
)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"📩 Получен запрос: {data}")
        update = Update.de_json(data, bot)

        # Обработка inline-кнопки "Инфо"
        if update.callback_query:
            query = update.callback_query
            chat_id = query.message.chat.id
            callback_data = query.data

            if callback_data.startswith("details_"):
                plant_name = callback_data.replace("details_", "")
                plant = get_plant_data(plant_name)
                if plant:
                    reply = format_plant_info_extended(plant)
                    bot.send_message(
                        chat_id=chat_id,
                        text=reply,
                        parse_mode=ParseMode.HTML,
                        reply_markup=info_keyboard
                    )
                else:
                    bot.send_message(
                        chat_id=chat_id,
                        text="❌ Растение не найдено.",
                        reply_markup=info_keyboard
                    )
                return JSONResponse(content={"status": "ok"})

        # Обработка текстовых сообщений
        if update.message and update.message.text:
            chat_id = update.message.chat.id
            text = update.message.text.strip()
            logger.info(f"🗣 Пользователь: {chat_id} → {text}")

            if text == "/start":
                bot.send_message(
                    chat_id=chat_id,
                    text="🌿 Напишите название растения, и бот покажет полную карточку с фото и советами.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=info_keyboard
                )
                return JSONResponse(content={"status": "ok"})

            if text == "📋 Подробнее":
                bot_info = get_bot_info()
                bot.send_message(
                    chat_id=chat_id,
                    text=bot_info,
                    parse_mode=ParseMode.HTML
                )
                return JSONResponse(content={"status": "ok"})

            if text == "🛒 Заказать услугу":
                bot.send_message(
                    chat_id=chat_id,
                    text="🛒 Заказ услуги: функция в разработке. Здесь появится описание и кнопка оплаты после диплоя.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=info_keyboard
                )
                return JSONResponse(content={"status": "ok"})

            # Отправка карточки с inline-кнопкой "Подробнее"
            plant = get_plant_data(text)
            if plant:
                reply = format_plant_info_base(plant)
                image_path = f"images/{plant.get('image')}"
                inline_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Подробнее", callback_data=f"details_{plant.get('name')}")]
                ])

                try:
                    with open(image_path, "rb") as image:
                        bot.send_photo(
                            chat_id=chat_id,
                            photo=image,
                            caption=reply,
                            parse_mode=ParseMode.HTML,
                            reply_markup=inline_keyboard,
                        )
                except FileNotFoundError:
                    bot.send_message(
                        chat_id=chat_id,
                        text=f"{reply}\n\n⚠️ Изображение не найдено.",
                        parse_mode=ParseMode.HTML,
                        reply_markup=inline_keyboard,
                    )
            else:
                bot.send_message(
                    chat_id=chat_id,
                    text="🌱 Растение не найдено. Попробуйте другое название.",
                    reply_markup=info_keyboard
                )

        return JSONResponse(content={"status": "ok"})

    except TelegramError as e:
        logger.error(f"❌ Ошибка Telegram: {e}")
        return JSONResponse(content={"status": "error", "details": str(e)}, status_code=500)
    except Exception as e:
        logger.error(f"❌ Общая ошибка: {e}")
        return JSONResponse(content={"status": "error", "details": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
