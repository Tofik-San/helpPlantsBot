import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Bot, Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, MessageHandler, Filters, CallbackQueryHandler
from service import get_plant_data, format_plant_info_base, format_plant_info_extended, get_bot_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)
app = FastAPI()

dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

def handle_message(update: Update, context):
    text = update.message.text.lower()

    if text in ["🌵 суккуленты", "🌿 неприхотливые зелёные", "🌺 цветущие", "🍃 лианы"]:
        plants = get_plant_data()
        category = text.split()[1]
        matching_plants = [plant for plant in plants if category in plant.get('category_type', '').lower()]

        if matching_plants:
            buttons = [[InlineKeyboardButton(plant['name'], callback_data=f"plant_{plant['id']}")] for plant in matching_plants]
            reply_markup = InlineKeyboardMarkup(buttons)
            update.message.reply_text(f"Выберите растение из категории {text}:", reply_markup=reply_markup)
        else:
            update.message.reply_text(f"В категории {text} пока нет доступных растений.")

    else:
        keyboard = [
            [KeyboardButton("🌵 Суккуленты")],
            [KeyboardButton("🌿 Неприхотливые зелёные")],
            [KeyboardButton("🌺 Цветущие")],
            [KeyboardButton("🍃 Лианы")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        update.message.reply_text("Привет! 🌿 Выберите категорию:", reply_markup=reply_markup)

def handle_callback_query(update: Update, context):
    query = update.callback_query
    query.answer()
    data = query.data

    if data.startswith("plant_"):
        plant_id = int(data.split("_")[1])
        plant = get_plant_data(plant_id)

        if plant:
            caption, image_path = format_plant_info_base(plant)
            button = InlineKeyboardMarkup([[InlineKeyboardButton("📖 Статья", callback_data=f"details_{plant_id}")]])
            context.bot.send_photo(chat_id=query.message.chat_id, photo=image_path, caption=caption, parse_mode='HTML', reply_markup=button)
        else:
            query.edit_message_text("Не удалось найти растение.")

    elif data.startswith("details_"):
        plant_id = int(data.split("_")[1])
        plant = get_plant_data(plant_id)
        if plant:
            extended_info = format_plant_info_extended(plant)
            query.edit_message_text(extended_info, parse_mode='HTML')
        else:
            query.edit_message_text("Не удалось найти подробности по растению.")

dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))

@app.post('/webhook')
async def webhook_handler(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return JSONResponse(content={"status": "ok"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
