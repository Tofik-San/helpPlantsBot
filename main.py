from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import (
    Bot,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
import logging
import os

from service import (
    get_plant_data,
    get_bot_info,
    list_varieties_by_category,
    format_plant_info_base,
    format_plant_info_extended,
    format_plant_insights
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = FastAPI()

CATEGORY_INFO = {
    "Суккуленты": {
        "title": "Суккуленты 🌵",
        "description": "Растения, способные накапливать влагу. Отличный выбор для тех, кто забывает поливать.",
        "image": "images/succulents.jpg"
    },
    "Лианы": {
        "title": "Лианы 🌿",
        "description": "Декоративные вьющиеся растения. Добавят объём и зелень в интерьере.",
        "image": "images/lians.jpg"
    },
    "Неприхотливые зелёные": {
        "title": "Неприхотливые зелёные 🌱",
        "description": "Минимум забот — максимум зелени. Идеальны для занятых.",
        "image": "images/green_easy.jpg"
    },
    "Цветущие": {
        "title": "Цветущие 🌸",
        "description": "Пышные и яркие. Для тех, кто хочет видеть цветение круглый год.",
        "image": "images/flowering.jpg"
    }
}


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


def generate_variety_keyboard(category, index, include_article=True):
    buttons = [
        InlineKeyboardButton("◀️", callback_data=f"list_varieties_{category}_{index - 1}")
    ]
    if include_article:
        buttons.append(InlineKeyboardButton("📖 Статья", callback_data=f"article_{category}_{index}"))
    buttons.append(InlineKeyboardButton("▶️", callback_data=f"list_varieties_{category}_{index + 1}"))
    return InlineKeyboardMarkup([buttons])


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
        bot.send_message(
            chat_id=update.message.chat.id,
            text="""🌿 О проекте BOTanik

(сокращено для экономии места)

📢 Канал проекта: https://t.me/BOTanikPlants
Связь по сотрудничеству: @veryhappyEpta""",
            reply_markup=get_persistent_keyboard()
        )
    elif text == "📢 Канал":
        bot.send_message(chat_id=update.message.chat.id, text="https://t.me/BOTanikPlants", reply_markup=get_persistent_keyboard())
    elif text == "❓ Help":
        bot.send_message(
            chat_id=update.message.chat.id,
            text="""❓ Help: Как пользоваться ботом

(сокращено)

Есть вопросы или предложения? Пиши: @veryhappyEpta
""",
            reply_markup=get_persistent_keyboard()
        )
    elif text == "📂 Категории":
        bot.send_message(chat_id=update.message.chat.id, text="Выбери категорию:", reply_markup=get_category_inline_keyboard())


# ✅ ASYNC callback
async def button_callback(update):
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Failed to answer callback query: {e}")
    data = query.data

    if data.startswith("category_"):
        category = data.split("_", 1)[1]
        info = CATEGORY_INFO.get(category)
        if info:
            try:
                with open(info["image"], "rb") as photo:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("📜 К сортам", callback_data=f"list_varieties_{category}_0")]
                    ])
                    await bot.send_photo(
                        chat_id=query.message.chat.id,
                        photo=photo,
                        caption=f"<b>{info['title']}</b>\n\n{info['description']}",
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            except Exception as e:
                logger.error(f"Ошибка при открытии фото категории {category}: {e}")
                await bot.send_message(chat_id=query.message.chat.id, text="Ошибка при загрузке изображения категории.")

    elif data.startswith("list_varieties_"):
        parts = data.split("_", 3)
        if len(parts) == 4:
            category = parts[2]
            index = int(parts[3])
            plant_list = list_varieties_by_category(category)
            if 0 <= index < len(plant_list):
                plant = plant_list[index]
                msg = format_plant_info_base(plant) + "\n\n" + format_plant_info_extended(plant)
                nav = generate_variety_keyboard(category, index, include_article=True)
                await bot.send_message(
                    chat_id=query.message.chat.id,
                    text=msg,
                    parse_mode="HTML",
                    reply_markup=nav
                )
            else:
                await bot.answer_callback_query(query.id, text="Дальше сортов нет.")

    elif data.startswith("article_"):
        parts = data.split("_", 2)
        if len(parts) == 3:
            category = parts[1]
            index = int(parts[2])
            plant_list = list_varieties_by_category(category)
            if 0 <= index < len(plant_list):
                plant = plant_list[index]
                article = format_plant_insights(plant) or "Статья отсутствует."
                nav = generate_variety_keyboard(category, index, include_article=False)
                await bot.send_message(
                    chat_id=query.message.chat.id,
                    text=f"📖 <b>Статья:</b>\n{article}",
                    parse_mode="HTML",
                    reply_markup=nav
                )


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    if update.message:
        handle_static_buttons(update)
    elif update.callback_query:
        await button_callback(update)
    return JSONResponse(content={"status": "ok"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
