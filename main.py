import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import (
    Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from service import get_plant_data, get_bot_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = FastAPI()

# Постоянная клавиатура для низа экрана
def get_persistent_keyboard():
    keyboard = [
        [KeyboardButton("🔄 Рестарт"), KeyboardButton("ℹ️ О проекте")],
        [KeyboardButton("📢 Канал")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Генерация inline-клавы категорий
def get_category_inline_keyboard():
    keyboard = [
        [InlineKeyboardButton("🪴 Суккуленты", callback_data="category_Суккуленты")],
        [InlineKeyboardButton("🌿 Неприхотливые зелёные", callback_data="category_Неприхотливые зелёные")],
        [InlineKeyboardButton("🌸 Цветущие", callback_data="category_Цветущие")],
        [InlineKeyboardButton("🌱 Лианы", callback_data="category_Лианы")]
    ]
    return InlineKeyboardMarkup(keyboard)

# /start
def start(update):
    reply_markup = get_category_inline_keyboard()
    bot.send_message(
        chat_id=update.message.chat.id,
        text="🌿 Привет! Я бот по растениям.\nВыберите категорию:",
        reply_markup=reply_markup
    )
    # Отправляем только клавиатуру без текста
    bot.send_message(
        chat_id=update.message.chat.id,
        text="\u200b",  # zero-width space чтобы отправить пустое сообщение
        reply_markup=get_persistent_keyboard()
    )

# Обработка текстовых кнопок (Канал, О проекте, Рестарт)
def handle_static_buttons(update):
    text = update.message.text.strip()
    if text == "🔄 Рестарт":
        start(update)
    elif text == "ℹ️ О проекте":
        bot.send_message(
            chat_id=update.message.chat.id,
            text="ℹ️ Этот бот помогает выбирать и ухаживать за растениями. Подробности добавлю позже."
        )
    elif text == "📢 Канал":
        bot.send_message(
            chat_id=update.message.chat.id,
            text="📢 Наш канал: https://t.me/+g4KcJjJAR7pkZWJi"
        )
    else:
        handle_message(update)

# Обработка сообщений
def handle_message(update):
    text = update.message.text.strip()
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
        start(update)

# Обработка кнопок inline
def button_callback(update):
    query = update.callback_query
    query.answer()
    data = query.data

    if data.startswith("category_"):
        category = data.split("_", 1)[1]
        plants = get_plant_data(category_filter=category)
        if plants:
            keyboard = [
                [InlineKeyboardButton(plant['name'], callback_data=f"plant_{plant['id']}")]
                for plant in plants
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.send_message(
                chat_id=query.message.chat.id,
                text="Выберите растение:",
                reply_markup=reply_markup
            )
        else:
            bot.send_message(
                chat_id=query.message.chat.id,
                text="В этой категории пока нет растений."
            )

    elif data.startswith("plant_"):
        plant_id = int(data.split("_")[1])
        plant_list = get_plant_data(id_filter=plant_id)
        if plant_list:
            plant = plant_list[0]
            photo_url = f"https://tofik-san.github.io/helpPlantsBot/images/{plant['image']}"
            caption = f"<b>{plant['name']}</b>\n{plant['short_description']}"
            keyboard = [[InlineKeyboardButton("📖 Подробнее", callback_data=f"details_{plant['id']}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.send_photo(
                chat_id=query.message.chat.id,
                photo=photo_url,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            bot.send_message(
                chat_id=query.message.chat.id,
                text="Ошибка при получении информации о растении."
            )

    elif data.startswith("details_"):
        plant_id = int(data.split("_")[1])
        plant_list = get_plant_data(id_filter=plant_id)
        if plant_list:
            plant = plant_list[0]
            detailed_info = (
                f"🌿 <b>Тип:</b> {plant['category_type']}\n"
                f"☀️ <b>Свет:</b> {plant['light']}\n"
                f"💧 <b>Полив:</b> {plant['watering']}\n"
                f"🌡️ <b>Температура:</b> {plant['temperature']}\n"
                f"🪴 <b>Почва:</b> {plant['soil']}\n"
                f"🌻 <b>Удобрения:</b> {plant['fertilizer']}\n"
                f"✂️ <b>Уход:</b> {plant['care_tip']}"
            )
            keyboard = [[InlineKeyboardButton("📖 Статья", callback_data=f"insights_{plant['id']}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.send_message(
                chat_id=query.message.chat.id,
                text=detailed_info,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            bot.send_message(
                chat_id=query.message.chat.id,
                text="Не удалось получить подробную информацию."
            )

    elif data.startswith("insights_"):
        plant_id = int(data.split("_")[1])
        plant_list = get_plant_data(id_filter=plant_id)
        if plant_list:
            plant = plant_list[0]
            insights_text = plant['insights'].replace("\\n", "\n")
            bot.send_message(
                chat_id=query.message.chat.id,
                text=insights_text
            )
        else:
            bot.send_message(
                chat_id=query.message.chat.id,
                text="Не удалось получить статью для этого растения."
            )

# Webhook
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)

    if update.message:
        handle_static_buttons(update)
    elif update.callback_query:
        button_callback(update)

    return JSONResponse(content={"status": "ok"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
