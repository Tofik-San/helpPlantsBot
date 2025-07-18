import os
import logging
import base64
import imghdr
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import httpx
from limit_checker import check_and_increment_limit

TOKEN = os.getenv("BOT_TOKEN")
PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

application = Application.builder().token(TOKEN).build()

INFO_TEXT = """📘 Как пользоваться ботом GreenCore

🧭 Как ориентироваться в ответе:

📸 Присылайте одно фото, не как файл, а как изображение.
📏 Максимальный размер — до 5 МБ, иначе бот не сможет его обработать.

🔍 После распознавания бот покажет название и уровень уверенности:
– 🟢 85–100% — совпадение почти наверняка
– 🟡 60–84% — возможно, стоит перепроверить
- 🔴 менее 60% — лучше отправить другое фото
💡 Если уверенность низкая:
– Сфотографируйте растение под другим углом
– Используйте естественное освещение
– Избегайте бликов, размытости и темноты

📷 Чем чище фото — тем точнее результат. Не жми, не прикладывай несколько сразу.


👋 Что делает бот:
– Отправьте фото растения — бот распознает его
– Получте карточку ухода: свет, полив, пересадка и другое
– Используйте кнопки снизу для доступа к каналу или описанию проекта

❗ Важно:
– Кнопка «О проекте» — расскажет об идее и будущем бота
– Кнопка «Канал» — даёт доступ к новостям и обновлениям
– В ближайшем обновлении появится: история распознаваний, подбор по условиям, и не только

🪴 Что бот уже умеет:
✅ Распознавать растение по фото
✅ Давать советы по уходу на основе внутренней базы
✅ Показывать уверенность распознавания
✅ Работать быстро и без лишних действий

📜 Политика использования:
– Бот бесплатен и создан для помощи в уходе за растениями
– Информация справочная и не заменяет консультации специалистов (пока что)
– Уважайте труд автора. Конструктив всегда приветствуется

🔔 Обновления и новые растения появляются регулярно — подпишитесь на канал, чтобы не пропустить:
https://t.me/BOTanikPlants

📬 Есть идеи или предложения? Пиши: @veryhappyEpta"""

ABOUT_TEXT = """🌿 О проекте: GreenCore

Изначально бот создавался как инструмент для системного ухода за растениями: с каталогом, планировщиком и ботами-модераторами.
Тогда это был BOTanik — проект, объединяющий базу растений, советы и автоматизацию.

Но всё быстро упёрлось в лимиты Telegram: можно было сделать красиво, но главная задача была в другом —
максимально быстро и точно, без лишних клацаний, дать пользователю то, что нужно.

🌀 Сейчас логика стала предельно чёткой:
Фото → Название → Уход
Никаких лишних действий. Только суть.

🧠 Что умеет PROplants сегодня:
– Определяет растение по фото
– Выдаёт карточку с рекомендациями по уходу
– Работает прямо в Telegram, без приложений и переходов

🛠️ Текущий стек:
– Python + FastAPI
– Telegram Bot API (webhook)
– httpx для сетевых запросов
– Plant.id API — для AI-распознавания
– JSON / SQLite — база растений

🚀 Ближайшие шаги:
✅ Расширение базы сортов
✅ Советы от GPT по контексту
✅ Распознавание болезней и вредителей
✅ Кастомные версии для питомников
✅ Интеграция мини-маркета

👥 Кому подойдёт:
– Владельцам домашних растений
– Озеленителям и дизайнерам
– Питомникам и магазинам
– Всем, кто хочет ухаживать проще, точнее и быстрее

💡 Почему это удобно:
– Не нужно искать — бот сам всё покажет
– Работает быстро и стабильно
– Подходит и новичкам, и опытным

📢 Канал проекта: https://t.me/BOTanikPlants
📬 Связь: @veryhappyEpta"""

CHANNEL_TEXT = "Наш канал: https://t.me/BOTanikPlants"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("📘 Инфо")],
                [KeyboardButton("📢 Канал"), KeyboardButton("ℹ️ О проекте")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! Я BOTanik! Отправь фото, и я попробую определить растение.",
        reply_markup=reply_markup,
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if update.message.media_group_id:
        await update.message.reply_text("📸 Отправьте, пожалуйста, только одно фото за раз.")
        return

    photo = update.message.photo[-1]
    if photo.file_size and photo.file_size > 5 * 1024 * 1024:
        await update.message.reply_text("❌ Не удалось распознать растение. Попробуйте другое фото.")
        return

    file = await context.bot.get_file(photo.file_id)
    path = "temp_photo"
    await file.download_to_drive(custom_path=path)

    if imghdr.what(path) not in ("jpeg", "png"):
        await update.message.reply_text("❌ Не удалось распознать растение. Попробуйте другое фото.")
        return

    if not await check_and_increment_limit(user_id):
        await update.message.reply_text("🚫 Лимит на сегодня исчерпан. Попробуйте завтра.")
        return

    with open(path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.plant.id/v2/identify",
            headers={"Api-Key": PLANT_ID_API_KEY},
            json={"images": [image_b64], "organs": ["leaf", "flower"]},
        )

    if resp.status_code != 200:
        logger.error(f"Plant.id API error {resp.status_code}: {resp.text}")
        await update.message.reply_text("❌ Не удалось распознать растение.")
        return

    data = resp.json()
    suggestions = data.get("suggestions")
    if not suggestions:
        await update.message.reply_text("❌ Не удалось распознать растение.")
        return

    top = suggestions[0]
    name = top.get("plant_name", "неизвестно")
    prob = round(top.get("probability", 0) * 100, 2)
    await update.message.reply_text(f"🌱 Похоже, это: {name} ({prob}%)")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📘 Инфо":
        await update.message.reply_text(INFO_TEXT)
    elif text == "📢 Канал":
        await update.message.reply_text(CHANNEL_TEXT)
    elif text == "ℹ️ О проекте":
        await update.message.reply_text(ABOUT_TEXT)


application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

if __name__ == "__main__":
    application.run_polling()
