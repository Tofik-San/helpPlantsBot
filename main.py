import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from service import get_plant_data, get_bot_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = FastAPI()

def get_persistent_keyboard():
    keyboard = [
        [KeyboardButton("📂 Категории"), KeyboardButton("❓ Help")],
        [KeyboardButton("📢 Канал"), KeyboardButton("ℹ️ О проекте")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_category_inline_keyboard():
    keyboard = [
        [InlineKeyboardButton("🪴 Суккуленты", callback_data="category_Суккуленты")],
        [InlineKeyboardButton("🌿 Неприхотливые зелёные", callback_data="category_Неприхотливые зелёные")],
        [InlineKeyboardButton("🌸 Цветущие", callback_data="category_Цветущие")],
        [InlineKeyboardButton("🌱 Лианы", callback_data="category_Лианы")]
    ]
    return InlineKeyboardMarkup(keyboard)

def start(update):
    bot.send_message(
        chat_id=update.message.chat.id,
        text="🌿 BOTanik готов к работе. Выбери действие кнопками внизу или нажми '📂 Категории'.",
        reply_markup=get_persistent_keyboard()
    )

def handle_static_buttons(update):
    text = update.message.text.strip()
    if text == "/start":
        start(update)
    elif text == "ℹ️ О проекте":
        bot.send_message(chat_id=update.message.chat.id, text=get_bot_info(), reply_markup=get_persistent_keyboard())
    elif text == "📢 Канал":
        bot.send_message(chat_id=update.message.chat.id, text="https://t.me/BOTanikPlants", reply_markup=get_persistent_keyboard())
    elif text == "❓ Help":
        bot.send_message(chat_id=update.message.chat.id, text="Бот BOTanik поможет выбрать и узнать, как ухаживать за растениями.", reply_markup=get_persistent_keyboard())
    elif text == "📂 Категории":
        bot.send_message(chat_id=update.message.chat.id, text="Выбери категорию:", reply_markup=get_category_inline_keyboard())
    else:
        handle_message(update)

def handle_message(update):
    text = update.message.text.strip()
    plant_list = get_plant_data(name=text)
    if plant_list:
        plant = plant_list[0]
        photo_url = f"https://tofik-san.github.io/helpPlantsBot/images/{plant['image']}"
        caption = f"<b>{plant['name']}</b>\n{plant['short_description']}"
        keyboard = [[InlineKeyboardButton("📖 Подробнее", callback_data=f"details_{plant['id']}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            bot.send_photo(chat_id=update.effective_chat.id, photo=photo_url, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            bot.send_message(chat_id=update.effective_chat.id, text=f"{caption}\n\n⚠️ Фото временно недоступно.", reply_markup=reply_markup, parse_mode="HTML")
    else:
        bot.send_message(chat_id=update.message.chat.id, text="Растение не найдено. Попробуй другое название или выбери категорию.", reply_markup=get_persistent_keyboard())

def button_callback(update):
    query = update.callback_query
    try:
        query.answer()
    except Exception as e:
        logger.warning(f"Failed to answer callback query: {e}")
    data = query.data

    if data.startswith("category_"):
        category = data.split("_", 1)[1]
        plants = get_plant_data(category_filter=category)
        if plants:
            keyboard = [[InlineKeyboardButton(plant['name'], callback_data=f"plant_{plant['id']}")] for plant in plants]
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.send_message(chat_id=query.message.chat.id, text="Выбери растение:", reply_markup=reply_markup)
        else:
            bot.send_message(chat_id=query.message.chat.id, text="В этой категории пока нет растений.", reply_markup=get_persistent_keyboard())

    elif data.startswith("plant_"):
        plant_id = int(data.split("_")[1])
        plant_list = get_plant_data(id_filter=plant_id)
        if plant_list:
            plant = plant_list[0]
            photo_url = f"https://tofik-san.github.io/helpPlantsBot/images/{plant['image']}"
            caption = f"<b>{plant['name']}</b>\n{plant['short_description']}"
            keyboard = [[InlineKeyboardButton("📖 Подробнее", callback_data=f"details_{plant['id']}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                bot.send_photo(chat_id=query.message.chat.id, photo=photo_url, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Ошибка при отправке фото: {e}")
                bot.send_message(chat_id=query.message.chat.id, text=f"{caption}\n\n⚠️ Фото временно недоступно.", reply_markup=reply_markup, parse_mode="HTML")
        else:
            bot.send_message(chat_id=query.message.chat.id, text="Ошибка при получении информации о растении.", reply_markup=get_persistent_keyboard())

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
            bot.send_message(chat_id=query.message.chat.id, text=detailed_info, parse_mode="HTML", reply_markup=reply_markup)
        else:
            bot.send_message(chat_id=query.message.chat.id, text="Не удалось получить подробную информацию.", reply_markup=get_persistent_keyboard())

    elif data.startswith("insights_"):
        plant_id = int(data.split("_")[1])
        plant_list = get_plant_data(id_filter=plant_id)
        if plant_list:
            plant = plant_list[0]
            insights_text = plant['insights'].replace("\\n", "\n")
            bot.send_message(chat_id=query.message.chat.id, text=insights_text, reply_markup=get_persistent_keyboard())
        else:
            bot.send_message(chat_id=query.message.chat.id, text="Не удалось получить статью для этого растения.", reply_markup=get_persistent_keyboard())

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
