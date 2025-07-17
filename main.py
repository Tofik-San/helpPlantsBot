import os
import logging
import traceback
import base64
import imghdr
from fastapi import FastAPI, Request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)
import httpx

# --- Конфиги
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")

# --- Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Telegram + FastAPI
app = FastAPI()
application = Application.builder().token(TOKEN).build()
app_state_ready = False

os.makedirs("temp", exist_ok=True)

# --- /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📘 Инфо")],
        [KeyboardButton("📢 Канал"), KeyboardButton("ℹ️ О проекте")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! Я BOTanik! Добро пожаловать в мою лабораторию GreenCore. 🌿\n"
        "Отправь фото — я распознаю растение и расскажу, как за ним ухаживать.",
        reply_markup=reply_markup
    )

# --- Обработка фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]
        # BLOCK 1: size check before downloading
        if photo.file_size and photo.file_size > 5 * 1024 * 1024:
            await update.message.reply_text(
                "❌ Не удалось распознать растение. Попробуйте другое фото.")
            logger.info(
                f"[BLOCK 1] Reject large file from user {update.effective_user.id}: {photo.file_size}")
            return

        file = await context.bot.get_file(photo.file_id)
        temp_path = "temp/plant.jpg"
        await file.download_to_drive(custom_path=temp_path)

        # BLOCK 1: format check
        img_type = imghdr.what(temp_path)
        if img_type not in ("jpeg", "png"):
            await update.message.reply_text(
                "❌ Не удалось распознать растение. Попробуйте другое фото.")
            logger.info(
                f"[BLOCK 1] Reject format {img_type} from user {update.effective_user.id}")
            return

        await update.message.reply_text("Распознаю растение…")

        with open(temp_path, "rb") as image_file:
            image_bytes = image_file.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.plant.id/v2/identify",
                headers={"Api-Key": PLANT_ID_API_KEY},
                json={
                    "images": [image_b64],
                    "organs": ["leaf", "flower"]
                }
            )

        result = response.json()
        # BLOCK 1: probability check from Plant.id
        is_plant_prob = result.get("is_plant_probability", 0)
        if is_plant_prob < 0.2:
            logger.info(
                f"[BLOCK 1] Low probability {is_plant_prob} from user {update.effective_user.id}")
            await update.message.reply_text(
                "❌ Не удалось распознать растение. Попробуйте другое фото.")
            return

        suggestions = result.get("suggestions", [])
        if not suggestions:
            await update.message.reply_text(
                "❌ Не удалось распознать растение. Попробуйте другое фото.")
            return

        top = suggestions[0]
        name = top.get("plant_name", "неизвестно")
        prob = round(top.get("probability", 0) * 100, 2)
        await update.message.reply_text(f"🌱 Похоже, это: {name} ({prob}%)")

    except Exception as e:
        logger.error(f"[handle_photo] Ошибка: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("Ошибка при распознавании растения.")

# --- Обработка текстовых кнопок
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "ℹ️ О проекте":
        await update.message.reply_text ("""🌿 О проекте: GreenCore

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
📬 Связь: @veryhappyEpta""")
    elif text == "📢 Канал":
        await update.message.reply_text("Наш канал: https://t.me/BOTanikPlants")
    elif text == "📘 Инфо":
        await update.message.reply_text("""📘 Как пользоваться ботом GreenCore

🧭 Как ориентироваться в ответе:

📸 Присылайте одно фото, не как файл, а как изображение.
📏 Максимальный размер — до 5 МБ, иначе бот не сможет его обработать.

🔍 После распознавания бот покажет название и уровень уверенности:
– 🟢 85–100% — совпадение почти наверняка
– 🟡 60–84% — возможно, стоит перепроверить
– 🔴 <60% — лучше отправить другое фото

💡 Если уверенность низкая:
– Сфотографируйте растение под другим углом
– Используйте естественное освещение
– Избегайте бликов, размытости и темноты

📷 Чем чище фото — тем точнее результат. Не жми, не прикладывай несколько сразу.


👋 Что делает бот:
– Отправьте фото растения — бот распознает его
– Получите карточку ухода: свет, полив, пересадка и другое
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

📬 Есть идеи или предложения? Пиши: @veryhappyEpta""")

# --- Хендлеры
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

# --- Инициализация
@app.on_event("startup")
async def startup():
    global app_state_ready
    try:
        await application.initialize()
        app_state_ready = True
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info("Webhook установлен.")
    except Exception as e:
        logger.error(f"[startup] Ошибка при инициализации: {e}\n{traceback.format_exc()}")

# --- Webhook
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        if not app_state_ready:
            logger.warning("Приложение не готово.")
            return {"ok": False, "error": "Not initialized"}
        await application.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"[webhook] Ошибка: {e}\n{traceback.format_exc()}")
        return {"ok": False, "error": str(e)}

# --- Запуск
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
