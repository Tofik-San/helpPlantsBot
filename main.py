import logging
import os
from fastapi import FastAPI, Request
from telegram import Bot, Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from service import get_plant_data, format_plant_info_base, format_plant_info_extended

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)
app = FastAPI()

dispatcher = Dispatcher(bot, None, use_context=True)

# Кнопки категорий
category_buttons = [
    [KeyboardButton("🪴 Суккуленты"), KeyboardButton("🌱 Неприхотливые зелёные")],
    [KeyboardButton("🌸 Цветущие"), KeyboardButton("🌿 Лианы")]
]
category_keyboard = ReplyKeyboardMarkup(category_buttons, resize_keyboard=True)

# /start
async def start(update: Update, context):
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text="🌿 Привет! Я бот по растениям.\nВыберите категорию:",
        reply_markup=category_keyboard
    )

# Сообщения
async def handle_message(update: Update, context):
    chat_id = update.effective_chat.id
    text = update.message.text.strip().lower()

    # Проверяем категории
    if "суккуленты" in text:
        plants = get_plant_data(category_filter="Суккуленты")
        names = [p['name'] for p in plants]
        buttons = [[KeyboardButton(name)] for name in names]
        markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        await context.bot.send_message(chat_id=chat_id, text="Выберите растение:", reply_markup=markup)
        return

    # Показываем карточку по названию
    plant = get_plant_data(name_filter=text)
    if plant:
        photo_url = f"https://tofik-san.github.io/helpPlantsBot/images/{plant['image']}"
        caption = format_plant_info_base(plant)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📄 Подробнее", callback_data=f"details_{plant['id']}")]])
        await context.bot.send_photo(chat_id=chat_id, photo=photo_url, caption=caption, parse_mode='HTML', reply_markup=keyboard)
    else:
        await context.bot.send_message(chat_id=chat_id, text="🌿 Растение не найдено. Попробуйте другое название.")

# Подробнее
async def button_callback(update: Update, context):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("details_"):
        plant_id = int(data.split("_")[1])
        plant = get_plant_data(id_filter=plant_id)
        if plant:
            text = format_plant_info_extended(plant)
            await query.message.reply_text(text, parse_mode='HTML')

# Регистрация хендлеров
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
dispatcher.add_handler(MessageHandler(Filters.callback_query, button_callback))

@app.post("/webhook")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), bot)
    await dispatcher.process_update(update)
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
