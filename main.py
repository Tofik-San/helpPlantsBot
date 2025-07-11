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

# Постоянная клавиатура (исправлено под твои пожелания)
def get_persistent_keyboard():
    keyboard = [
        [KeyboardButton("🔄 Рестарт"), KeyboardButton("ℹ️ О проекте"), KeyboardButton("📢 Канал")],
        [KeyboardButton("❓ Help")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Inline категории
def get_category_inline_keyboard():
    keyboard = [
        [InlineKeyboardButton("🪴 Суккуленты", callback_data="category_Суккуленты")],
        [InlineKeyboardButton("🌿 Неприхотливые зелёные", callback_data="category_Неприхотливые зелёные")],
        [InlineKeyboardButton("🌸 Цветущие", callback_data="category_Цветущие")],
        [InlineKeyboardButton("🌱 Лианы", callback_data="category_Лианы")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Старт
def start(update):
    bot.send_message(
        chat_id=update.message.chat.id,
        text="🌿 Выберите категорию ниже или используйте кнопки внизу для навигации:",
        reply_markup=get_persistent_keyboard()
    )
    bot.send_message(
        chat_id=update.message.chat.id,
        text="Выберите категорию:",
        reply_markup=get_category_inline_keyboard()
    )

# Обработка кнопок
def handle_static_buttons(update):
    text = update.message.text.strip()
    if text == "🔄 Рестарт":
        start(update)
    elif text == "ℹ️ О проекте":
        bot.send_message(
            chat_id=update.message.chat.id,
            text="""🌿 О проекте BOTanik

Этот бот задумывался как удобный инструмент для системного ухода за растениями и изучения ботаники, объединяющий каталог растений, советы по уходу и автоматизацию рутинных задач.

Проект создаётся с прицелом на питомники, магазины растений и частных энтузиастов, которые хотят просто и быстро получать справочную информацию о растениях и следить за их состоянием.

🛠️ Техническая составляющая:
– Telegram Bot API для удобного доступа через мессенджер.
– Python + FastAPI для стабильной и быстрой работы.
– PostgreSQL для хранения базы растений с возможностью расширения.
– Интеграция с дополнительными ботами (хелпер и постер) для модерации и автообновлений.
– Гибкая архитектура, позволяющая добавлять GPT для рекомендаций, распознавание растений по фото, трекинг состояния растений и настройку уведомлений.

🚀 Перспективы развития:
✅ Постепенное расширение базы растений и сортов.
✅ Интеграция GPT для персональных рекомендаций по уходу.
✅ Распознавание растений и определение болезней по фото.
✅ Создание маркетплейса для заказа растений напрямую через бот.
✅ Возможность кастомизации под бренд питомников и магазинов.

📚 Кому подходит BOTanik:
– Питомникам и магазинам для обслуживания клиентов и ведения каталога.
– Студентам и преподавателям для демонстрации ухода за растениями.
– Владельцам домашних растений для удобного доступа к рекомендациям и плану ухода.
– Ландшафтным дизайнерам как база подбора растений.

💡 Чем полезен:
– Сокращает время поиска информации о растениях.
– Учит правильному уходу.
– Дает быстрый доступ к информации в одном месте.
– Может стать точкой входа для развития питомника в цифровом формате.

📢 Канал проекта: https://t.me/BOTanik_Channel
Связь по сотрудничеству: @veryhappyEpta
""",
            reply_markup=get_persistent_keyboard()
        )
    elif text == "📢 Канал":
        bot.send_message(
            chat_id=update.message.chat.id,
            text="https://t.me/BOTanik_Channel",
            reply_markup=get_persistent_keyboard()
        )
    elif text == "❓ Help":
        bot.send_message(
            chat_id=update.message.chat.id,
            text="""❓ Help: Как пользоваться ботом BOTanik

👋 Как работает бот:
– Выберите категорию, чтобы получить карточку с фото и рекомендациями по уходу.
– Используйте кнопки внизу экрана для быстрого доступа к функциям.
– Для ознакомления проекта кнопка "О проекте".
– Для перехода на канал кнопка "Канал" или ниже по ссылке.
– Кнопка "Рестарт" чтобы перейти к выбору категории.

🪴 Что бот умеет:
✅ Выдача краткой карточки с фото, описанием и советами по уходу.
✅ Пошаговые инструкции и советы по категориям.

📜 Политика бота:
– Бот бесплатный и предназначен для помощи в уходе за растениями.
– Информация носит справочный характер и не заменяет консультации специалистов (ПОКА ЧТО).
– Уважайте работу автора, не используйте бот для спама. Советы и конструктивная критика приветствуется.

🔔 Растения, гайды и статьи добавляются постепенно и чтобы не пропустить обновления, подпишись на наш канал:
https://t.me/BOTanik_Channel

Есть вопросы или предложения? Пиши: @veryhappyEpta
""",
            reply_markup=get_persistent_keyboard()
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

# Обработка inline кнопок
def button_callback(update):
    query = update.callback_query
    query.answer()
    data = query.data

    if data.startswith("category_"):
        category = data.split("_", 1)[1]
        plants = get_plant_data(category_filter=category)
        if plants:
            keyboard = [[InlineKeyboardButton(plant['name'], callback_data=f"plant_{plant['id']}")] for plant in plants]
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.send_message(chat_id=query.message.chat.id, text="Выберите растение:", reply_markup=reply_markup)
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
            bot.send_photo(chat_id=query.message.chat.id, photo=photo_url, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
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
