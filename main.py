import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from service import get_plant_data, paginate_plants
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = FastAPI()

# Храним текущую страницу для каждого пользователя в словаре
user_pages = defaultdict(int)

# Основная клавиатура
def get_persistent_keyboard():
    keyboard = [
        [KeyboardButton("📂 Категории"), KeyboardButton("❓ Help")],
        [KeyboardButton("📢 Канал"), KeyboardButton("ℹ️ О проекте")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Клавиатура для выбора категории
def get_category_inline_keyboard():
    keyboard = [
        [InlineKeyboardButton("🪴 Суккуленты", callback_data="category_succulents")],
        [InlineKeyboardButton("🌿 Неприхотливые зелёные", callback_data="category_easy_plants")],
        [InlineKeyboardButton("🌸 Цветущие", callback_data="category_flowering_plants")],
        [InlineKeyboardButton("🌱 Лианы", callback_data="category_vines")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Данные о категориях (картинки и описания)
category_data = {
    "succulents": {
        "description": "Суккуленты — это растения, которые способны накапливать воду в своих тканях...",
        "image": "images/succulents.jpg"
    },
    "easy_plants": {
        "description": "Неприхотливые растения, которые легко выращивать в домашних условиях...",
        "image": "images/easy_plants.jpg"
    },
    "flowering_plants": {
        "description": "Цветущие растения, которые украсят ваш дом...",
        "image": "images/flowering_plants.jpg"
    },
    "vines": {
        "description": "Лианы, которые могут использоваться как декоративные растения...",
        "image": "images/vines.jpg"
    }
}

# Стартовое сообщение
def start(update):
    bot.send_message(
        chat_id=update.message.chat.id,
        text="🌿 BOTanik готов к работе. Выбери действие кнопками внизу или нажми '📂 Категории'.",
        reply_markup=get_persistent_keyboard()
    )

# Обработка статических кнопок (помощь, канал, категории)
def handle_static_buttons(update):
    text = update.message.text.strip()
    if text == "/start":
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

📢 Канал проекта: https://t.me/BOTanikPlants
Связь по сотрудничеству: @veryhappyEpta""",
            reply_markup=get_persistent_keyboard()
        )
    elif text == "📢 Канал":
        bot.send_message(chat_id=update.message.chat.id, text="https://t.me/BOTanikPlants", reply_markup=get_persistent_keyboard())
    elif text == "❓ Help":
        bot.send_message(
            chat_id=update.message.chat.id,
            text="""❓ Help: Как пользоваться ботом BOTanik

👋 Как работает бот:
– Выберите категорию, чтобы получить карточку с фото и рекомендациями по уходу.
– Используйте кнопки внизу экрана для быстрого доступа к функциям.
- для ознакомления проекта кнопка "О проекте".
- для перехода на канал кнопка "Канал" или ниже по ссылке.
- кнопка "Категории" чтобы перейти к выбору категории.

🪴 Что бот умеет:
✅ Выдача краткой карточки с фото, описанием и советами по уходу.
✅ Пошаговые инструкции и советы по категориям.

📜 Политика бота:
– Бот бесплатный и предназначен для помощи в уходе за растениями.
– Информация носит справочный характер и не заменяет консультации специалистов (ПОКА ЧТО).
– Уважайте работу автора, не используйте бот для спама. Советы и конструктивная критика приветствуется.

🔔Растения, гайды и статьи добавляются постепенно и чтобы не пропустить обновления, подпишись на наш канал:
https://t.me/BOTanikPlants

Есть вопросы или предложения? Пиши: @veryhappyEpta
""",
            reply_markup=get_persistent_keyboard()
        )
    elif text == "📂 Категории":
        bot.send_message(chat_id=update.message.chat.id, text="Выбери категорию:", reply_markup=get_category_inline_keyboard())
    else:
        handle_message(update)

# Обработка нажатия кнопки категории
def button_callback(update):
    query = update.callback_query
    data = query.data

    if data.startswith("category_"):
        category = data.split("_", 1)[1]
        
        # Извлекаем данные для выбранной категории
        category_info = category_data.get(category)

        if category_info:
            image_path = category_info["image"]
            description = category_info["description"]

            try:
                # Отправляем изображение и описание
                if os.path.exists(image_path):
                    bot.send_photo(
                        chat_id=query.message.chat.id,
                        photo=open(image_path, 'rb'),
                        caption=f"Информация о категории {category}\n\n{description}",
                        reply_markup=InlineKeyboardMarkup([ 
                            [InlineKeyboardButton("📖 К сортам", callback_data=f"plants_{category}")]
                        ])
                    )
                else:
                    bot.send_message(chat_id=query.message.chat.id, text=f"Ошибка: файл для категории {category} не найден!")
            except Exception as e:
                bot.send_message(chat_id=query.message.chat.id, text=f"Ошибка при загрузке изображения категории {category}: {e}")
        else:
            bot.send_message(chat_id=query.message.chat.id, text="Ошибка: такая категория не найдена.", reply_markup=get_persistent_keyboard())

    # Обработка нажатия кнопки сортов
    elif data.startswith("plants_"):
        plant_type = data.split("_", 1)[1]
        
        # Получаем сорта для выбранной категории (фильтруем по category_name)
        plant_list = get_plant_data(category_filter=plant_type)

        if plant_list:
            # Храним текущую страницу для каждого пользователя
            user_id = query.from_user.id
            user_pages[user_id] = {
                'category': plant_type,
                'plants': paginate_plants(plant_list), # Пагинируем растения
                'current_page': 0
            }

            # Отправляем первую страницу сортов
            send_plant_page(update, user_id)
        else:
            bot.send_message(chat_id=query.message.chat.id, text="В этой категории пока нет растений.", reply_markup=get_persistent_keyboard())

    elif data.startswith("details_"):
        plant_id = int(data.split("_")[1])
        plant_list = get_plant_data(id_filter=plant_id)
        if plant_list:
            plant = plant_list[0]
            detailed_info = (
                f"🌿 <b>Тип:</b> {plant['category_name']}\n"
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

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    if update.message:
        handle_static_buttons(update)
    elif update.callback_query:
        button_callback(update)
    return JSONResponse(content={"status": "ok"})

def paginate_plants(plant_list, page_size=5):
    """Разбиваем список сортов на страницы с заданным количеством элементов (по 5 сортов на страницу)."""
    return [plant_list[i:i + page_size] for i in range(0, len(plant_list), page_size)]

def send_plant_page(update, user_id):
    """Отправляем страницу с сортами для данного пользователя"""
    user_data = user_pages[user_id]
    page = user_data['current_page']
    category = user_data['category']
    pages = user_data['plants']
    
    # Получаем текущие сорта для страницы
    plant_page = pages[page]
    plant_names = "\n".join([plant['name'] for plant in plant_page])
    
    # Кнопки "Далее" и "Назад"
    keyboard = []
    if page > 0:
        keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="prev")])
    if page < len(pages) - 1:
        keyboard.append([InlineKeyboardButton("Далее ➡", callback_data="next")])
    
    # Отправляем сообщение с сортами
    bot.send_message(
        chat_id=update.message.chat.id,
        text=f"Сорта в категории {category}:\n\n{plant_names}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
