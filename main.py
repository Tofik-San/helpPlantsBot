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

# Генерация клавиатуры с категориями и статичными кнопками
def get_category_keyboard():
    keyboard = [
        [InlineKeyboardButton("🪴 Суккуленты", callback_data="category_Суккуленты")],
        [InlineKeyboardButton("🌿 Неприхотливые зелёные", callback_data="category_Неприхотливые зелёные")],
        [InlineKeyboardButton("🌸 Цветущие", callback_data="category_Цветущие")],
        [InlineKeyboardButton("🌱 Лианы", callback_data="category_Лианы")],
        [InlineKeyboardButton("🔄 Рестарт", callback_data="restart"),
         InlineKeyboardButton("ℹ️ О проекте", callback_data="about")],
        [InlineKeyboardButton("📢 Канал", url="https://t.me/+g4KcJjJAR7pkZWJi")]
    ]
    return InlineKeyboardMarkup(keyboard)

# /start
def start(update):
    reply_markup = get_category_keyboard()
    bot.send_message(
        chat_id=update.message.chat.id,
        text="🌿 Привет! Я бот по растениям.\nВыберите категорию или перейдите в канал:",
        reply_markup=reply_markup
    )

# Обработка сообщений
def handle_message(update):
    text = update.message.text.strip()
    if text == "/start":
        start(update)
        return

    plant_list = get_plant_data(name=text)
    if plant_list:
        plant = plant_list[0]
        photo_url = f"https://tofik-san.github.io/helpPlantsBot/images/{plant['image']}"
        caption = f"<b>{plant['name']}</b>\n{plant['short_description']}"
        keyboard = [[InlineKeyboardButton("📖 Подробнее", callback_data=f"details_{plant['id']}")],
                    [InlineKeyboardButton("🔄 Рестарт", callback_data="restart"),
                     InlineKeyboardButton("ℹ️ О проекте", callback_data="about")],
                    [InlineKeyboardButton("📢 Канал", url="https://t.me/+g4KcJjJAR7pkZWJi")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_url,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        bot.send_message(
            chat_id=update.message.chat.id,
            text="🌿 Растение не найдено. Попробуйте другое название или выберите категорию ниже.",
            reply_markup=get_category_keyboard()
        )

# Обработка кнопок
def button_callback(update):
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "restart":
        bot.send_message(
            chat_id=query.message.chat.id,
            text="🔄 Вы вернулись к выбору категорий.",
            reply_markup=get_category_keyboard()
        )

    elif data == "about":
        bot.send_message(
            chat_id=query.message.chat.id,
            text="ℹ️ Этот бот помогает выбирать и ухаживать за растениями. Подробности добавлю позже.",
            reply_markup=get_category_keyboard()
        )

    elif data.startswith("category_"):
        category = data.split("_", 1)[1]
        plants = get_plant_data(category_filter=category)
        if plants:
            keyboard = [
                [InlineKeyboardButton(plant['name'], callback_data=f"plant_{plant['id']}")]
                for plant in plants
            ]
            keyboard.append([
                InlineKeyboardButton("🔄 Рестарт", callback_data="restart"),
                InlineKeyboardButton("ℹ️ О проекте", callback_data="about")
            ])
            keyboard.append([InlineKeyboardButton("📢 Канал", url="https://t.me/+g4KcJjJAR7pkZWJi")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.send_message(
                chat_id=query.message.chat.id,
                text="Выберите растение:",
                reply_markup=reply_markup
            )
        else:
            bot.send_message(
                chat_id=query.message.chat.id,
                text="В этой категории пока нет растений.",
                reply_markup=get_category_keyboard()
            )

    elif data.startswith("plant_"):
        plant_id = int(data.split("_")[1])
        plant_list = get_plant_data(id_filter=plant_id)
        if plant_list:
            plant = plant_list[0]
            photo_url = f"https://tofik-san.github.io/helpPlantsBot/images/{plant['image']}"
            caption = f"<b>{plant['name']}</b>\n{plant['short_description']}"
            keyboard = [[InlineKeyboardButton("📖 Подробнее", callback_data=f"details_{plant['id']}")],
                        [InlineKeyboardButton("🔄 Рестарт", callback_data="restart"),
                         InlineKeyboardButton("ℹ️ О проекте", callback_data="about")],
                        [InlineKeyboardButton("📢 Канал", url="https://t.me/+g4KcJjJAR7pkZWJi")]]
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
                text="Ошибка при получении информации о растении.",
                reply_markup=get_category_keyboard()
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
            keyboard = [[InlineKeyboardButton("📖 Статья", callback_data=f"insights_{plant['id']}")],
                        [InlineKeyboardButton("🔄 Рестарт", callback_data="restart"),
                         InlineKeyboardButton("ℹ️ О проекте", callback_data="about")],
                        [InlineKeyboardButton("📢 Канал", url="https://t.me/+g4KcJjJAR7pkZWJi")]]
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
                text="Не удалось получить подробную информацию.",
                reply_markup=get_category_keyboard()
            )

    elif data.startswith("insights_"):
        plant_id = int(data.split("_")[1])
        plant_list = get_plant_data(id_filter=plant_id)
        if plant_list:
            plant = plant_list[0]
            insights_text = plant['insights'].replace("\\n", "\n")
            keyboard = [
                [InlineKeyboardButton("🔄 Рестарт", callback_data="restart"),
                 InlineKeyboardButton("ℹ️ О проекте", callback_data="about")],
                [InlineKeyboardButton("📢 Канал", url="https://t.me/+g4KcJjJAR7pkZWJi")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.send_message(
                chat_id=query.message.chat.id,
                text=insights_text,
                reply_markup=reply_markup
            )
        else:
            bot.send_message(
                chat_id=query.message.chat.id,
                text="Не удалось получить статью для этого растения.",
                reply_markup=get_category_keyboard()
            )

# Webhook
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)

    if update.message:
        if update.message.text == "/start":
            start(update)
        else:
            handle_message(update)
    elif update.callback_query:
        button_callback(update)

    return JSONResponse(content={"status": "ok"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
