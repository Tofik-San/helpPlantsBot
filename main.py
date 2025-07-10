import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import (
    Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
)
from service import get_plant_data, get_bot_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = FastAPI()

# /start
def start(update):
    keyboard = [
        [InlineKeyboardButton("🪴 Суккуленты", callback_data="category_Суккуленты")],
        [InlineKeyboardButton("🌿 Неприхотливые зелёные", callback_data="category_Неприхотливые зелёные")],
        [InlineKeyboardButton("🌸 Цветущие", callback_data="category_Цветущие")],
        [InlineKeyboardButton("🌱 Лианы", callback_data="category_Лианы")],
        [InlineKeyboardButton("📢 Канал", url="https://t.me/+g4KcJjJAR7pkZWJi")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "🌿 Привет! Я бот по растениям.\nВыберите категорию или перейдите в канал:",
        reply_markup=reply_markup
    )

# Обработка сообщений
def handle_message(update):
    text = update.message.text.strip()
    if text == "📢 Канал":
        update.message.reply_text(
            "🔗 Наш канал: https://t.me/+g4KcJjJAR7pkZWJi"
        )
        return

    plant_list = get_plant_data(name=text)
    if plant_list:
        plant = plant_list[0]
        photo_url = f"https://tofik-san.github.io/helpPlantsBot/images/{plant['image']}"
        caption = f"<b>{plant['name']}</b>\n{plant['short_description']}"
        keyboard = [[InlineKeyboardButton("📖 Подробнее", callback_data=f"details_{plant['id']}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_url,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        update.message.reply_text("🌿 Растение не найдено. Попробуйте другое название.")

# Обработка кнопок
def button_callback(update):
    query = update.callback_query
    bot.answer_callback_query(callback_query_id=query.id)  # исправлен
