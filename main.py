from fastapi import FastAPI, Request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from service import get_plant_data
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = FastAPI()
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# /start
def start(update, context):
    keyboard = [
        [InlineKeyboardButton("🪴 Суккуленты", callback_data="category_Суккуленты")],
        [InlineKeyboardButton("🌿 Неприхотливые зелёные", callback_data="category_Неприхотливые зелёные")],
        [InlineKeyboardButton("🌸 Цветущие", callback_data="category_Цветущие")],
        [InlineKeyboardButton("🌱 Лианы", callback_data="category_Лианы")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("🌿 Привет! Я бот по растениям.\nВыберите категорию:", reply_markup=reply_markup)

# Обработка сообщений
def handle_message(update, context):
    text = update.message.text.strip()
    plant_list = get_plant_data(name=text)
    if plant_list:
        plant = plant_list[0]
        photo_url = f"https://tofik-san.github.io/helpPlantsBot/images/{plant['image']}"
        caption = f"<b>{plant['name']}</b>\n{plant['short_description']}"
        keyboard = [[InlineKeyboardButton("📖 Подробнее", callback_data=f"details_{plant['id']}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_url,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        update.message.reply_text("🌿 Растение не найдено. Попробуйте другое название.")

# Обработка кнопок
def button_callback(update, context):
    query = update.callback_query
    query.answer()

    data = query.data

    if data.startswith("category_"):
        category = data.split("_", 1)[1]
        plants = get_plant_data(category=category)
        if plants:
            keyboard = [
                [InlineKeyboardButton(plant['name'], callback_data=f"plant_{plant['id']}")]
                for plant in plants
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.reply_text("Выберите растение:", reply_markup=reply_markup)
        else:
            query.message.reply_text("В этой категории пока нет растений.")

    elif data.startswith("plant_"):
        plant_id = int(data.split("_")[1])
        plant_list = get_plant_data(id=plant_id)
        if plant_list:
            plant = plant_list[0]
            photo_url = f"https://tofik-san.github.io/helpPlantsBot/images/{plant['image']}"
            caption = f"<b>{plant['name']}</b>\n{plant['short_description']}"
            keyboard = [[InlineKeyboardButton("📖 Подробнее", callback_data=f"details_{plant['id']}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=photo_url,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            query.message.reply_text("Ошибка при получении информации о растении.")

    elif data.startswith("details_"):
        plant_id = int(data.split("_")[1])
        plant_list = get_plant_data(id=plant_id)
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
            context.bot.send_message(
                chat_id=query.message.chat_id,
                text=detailed_info,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            query.message.reply_text("Не удалось получить подробную информацию.")

    elif data.startswith("insights_"):
        plant_id = int(data.split("_")[1])
        plant_list = get_plant_data(id=plant_id)
        if plant_list:
            plant = plant_list[0]
            insights_text = plant['insights']
            context.bot.send_message(
                chat_id=query.message.chat_id,
                text=insights_text
            )
        else:
            query.message.reply_text("Не удалось получить статью для этого растения.")

# Handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
dispatcher.add_handler(CallbackQueryHandler(button_callback))

# Webhook
@app.post("/webhook")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), bot)
    dispatcher.process_update(update)
    return "ok"
