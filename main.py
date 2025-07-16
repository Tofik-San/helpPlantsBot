
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
            text="Описание проекта...",
            reply_markup=get_persistent_keyboard()
        )
    elif text == "📢 Канал":
        bot.send_message(chat_id=update.message.chat.id, text="https://t.me/BOTanikPlants", reply_markup=get_persistent_keyboard())
    elif text == "❓ Help":
        bot.send_message(
            chat_id=update.message.chat.id,
            text="Помощь и инструкции...",
            reply_markup=get_persistent_keyboard()
        )
    elif text == "📂 Категории":
        bot.send_message(chat_id=update.message.chat.id, text="Выбери категорию:", reply_markup=get_category_inline_keyboard())


def button_callback(update):
    query = update.callback_query
    try:
        query.answer()
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
                    bot.send_photo(
                        chat_id=query.message.chat.id,
                        photo=photo,
                        caption=f"<b>{info['title']}</b>

{info['description']}",
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            except Exception as e:
                logger.error(f"Ошибка при открытии фото категории {category}: {e}")
                bot.send_message(chat_id=query.message.chat.id, text="Ошибка при загрузке изображения категории.")

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
                bot.send_message(
                    chat_id=query.message.chat.id,
                    text=msg,
                    parse_mode="HTML",
                    reply_markup=nav
                )
            else:
                bot.answer_callback_query(query.id, text="Дальше сортов нет.")

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
                bot.send_message(
                    chat_id=query.message.chat.id,
                    text=f"📖 <b>Статья:</b>\n{article}",
                    parse_mode="HTML",
                    reply_markup=nav
                )



@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)

    if update.message and update.message.photo:
        file_id = update.message.photo[-1].file_id
        file = await bot.get_file(file_id)

        if not os.path.exists("temp"):
            os.makedirs("temp")

        photo_path = f"temp/{file_id}.jpg"
        await file.download_to_drive(photo_path)

        await bot.send_message(
            chat_id=update.message.chat.id,
            text="🔄 Обрабатываю фото..."
        )

        from service import identify_plant, get_plant_data, format_plant_info_base, format_plant_info_extended

        result = await identify_plant(photo_path)
        if "error" in result:
            await bot.send_message(
                chat_id=update.message.chat.id,
                text="🚫 Не удалось определить растение. Попробуйте другое фото."
            )
            return JSONResponse(content={"status": "plant_id_error"})

        latin_name = result["latin_name"]
        probability = result["probability"]

        await bot.send_message(
            chat_id=update.message.chat.id,
            text=f"🌿 Похоже, это <b>{latin_name}</b>
(уверенность: {probability}%)",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Уход", callback_data=f"care_{latin_name}")]
            ])
        )

        return JSONResponse(content={"status": "plant_identified"})

    if update.message:
        handle_static_buttons(update)

    elif update.callback_query:
        data = update.callback_query.data

        if data.startswith("care_"):
            latin = data.split("_", 1)[1]
            plant_list = get_plant_data(name=latin)
            if plant_list:
                plant = plant_list[0]
                msg = format_plant_info_base(plant) + "

" + format_plant_info_extended(plant)
                await bot.send_message(
                    chat_id=update.callback_query.message.chat.id,
                    text=msg,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=update.callback_query.message.chat.id,
                    text="❌ Нет информации о таком растении."
                )
        else:
            button_callback(update)

    return JSONResponse(content={"status": "ok"})



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
