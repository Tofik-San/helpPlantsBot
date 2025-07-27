import os
import logging
import traceback
import base64
import imghdr
from datetime import datetime
from fastapi import FastAPI, Request
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from openai import AsyncOpenAI
import httpx
from limit_checker import check_and_increment_limit
from service import get_card_by_latin_name, save_card

# --- Конфиги
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
DEBUG_GPT = os.getenv("DEBUG_GPT") == "1"

# --- Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Filter to avoid leaking the bot token in logs
class _TokenFilter(logging.Filter):
    def __init__(self, token: str) -> None:
        super().__init__()
        self.token = token or ""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - simple sanitization
        if self.token:
            token_mask = "<TOKEN>"
            record.msg = str(record.msg).replace(self.token, token_mask)
            if record.args:
                record.args = tuple(
                    str(arg).replace(self.token, token_mask) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True

logging.getLogger().addFilter(_TokenFilter(TOKEN))

# BLOCK 7: silence httpx logs and prevent propagation
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpx").propagate = False

# --- Telegram + FastAPI
app = FastAPI()
application = Application.builder().token(TOKEN).build()
app_state_ready = False

# BLOCK 1: storage for last recognition timestamps
user_last_request = {}

os.makedirs("temp", exist_ok=True)

def strip_tags(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", text)

def clean_description(data: dict) -> dict:
    name = data.get("name", "").strip()
    desc = data.get("short_description", "").strip()

    desc_cleaned = strip_tags(desc)
    if name and desc_cleaned.startswith(name):
        desc_cleaned = desc_cleaned[len(name):].strip(" .,\n")

    data["short_description"] = desc_cleaned
    return data


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
        reply_markup=reply_markup,
        parse_mode="HTML",
    )

# --- Обработка фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        now = datetime.utcnow()

        # BLOCK 1: check for multiple photos (albums)
        if update.message.media_group_id:
            await update.message.reply_text(
                "📸 Отправьте, пожалуйста, только одно фото за раз.",
                parse_mode="HTML",
            )
            logger.info(
                f"[BLOCK 1] Refuse album user {user_id} at {now.isoformat()} reason=album")
            return

        # BLOCK 1: rate limiting between recognitions
        last_time = user_last_request.get(user_id)
        if last_time and (now - last_time).total_seconds() < 15:
            await update.message.reply_text(
                "⏱ Подождите 15 секунд перед новой попыткой.",
                parse_mode="HTML",
            )
            logger.info(
                f"[BLOCK 1] Rate limit user {user_id} at {now.isoformat()} reason=rate_limit")
            return
        user_last_request[user_id] = now

        photo = update.message.photo[-1]
        # BLOCK 1: size check before downloading
        if photo.file_size and photo.file_size > 5 * 1024 * 1024:
            await update.message.reply_text(
                "❌ Не удалось распознать растение. Попробуйте другое фото.",
                parse_mode="HTML",
            )
            logger.info(
                f"[BLOCK 1] Reject large file from user {user_id} at {datetime.utcnow().isoformat()} size={photo.file_size} reason=size")
            return

        file = await context.bot.get_file(photo.file_id)
        temp_path = "temp/plant.jpg"
        await file.download_to_drive(custom_path=temp_path)

        # BLOCK 1: format check
        img_type = imghdr.what(temp_path)
        if img_type not in ("jpeg", "png"):
            await update.message.reply_text(
                "❌ Не удалось распознать растение. Попробуйте другое фото.",
                parse_mode="HTML",
            )
            logger.info(
                f"[BLOCK 1] Reject format {img_type} from user {user_id} at {datetime.utcnow().isoformat()} reason=format")
            return

        # BLOCK 2: daily usage limit
        if not await check_and_increment_limit(user_id):
            await update.message.reply_text(
                "🚫 Лимит на сегодня исчерпан. Попробуйте завтра.",
                parse_mode="HTML",
            )
            return

        await update.message.reply_text(
            "Распознаю растение…",
            parse_mode="HTML",
        )

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

        suggestions = result.get("suggestions", [])
        if not suggestions:
            await update.message.reply_text(
                "❌ Не удалось распознать растение. Попробуйте другое фото.",
                parse_mode="HTML",
            )
            logger.info(
                f"[BLOCK 1] No suggestions for user {user_id} at {datetime.utcnow().isoformat()} prob={is_plant_prob} reason=no_suggestions")
            return

        top = suggestions[0]
        name = top.get("plant_name", "неизвестно")
        prob = round(top.get("probability", 0) * 100, 2)

        # BLOCK 1.2: фильтрация мусора
        if is_plant_prob >= 0.2:
            # BLOCK 5: кнопка ухода
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🧠 Уход от BOTanika", callback_data=f"care:{name}")]]
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🌱 Похоже, это: {name} ({prob}%)",
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        else:
            logger.info(
                f"[BLOCK 1.2] Low probability {is_plant_prob} for user {user_id}"
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Не удалось распознать растение. Попробуйте другое фото.",
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"[handle_photo] Ошибка: {e}\n{traceback.format_exc()}")
        await update.message.reply_text(
            "Ошибка при распознавании растения.",
            parse_mode="HTML",
        )

# BLOCK 5: обработка карточки ухода через PostgreSQL и GPT-4
async def get_care_card_html(latin_name: str) -> str | None:
    """RAG: Поиск чанков ухода по FAISS и генерация карточки GPT."""
    import html
    from loguru import logger
    from faiss_search import get_chunks_by_latin_name
    from openai import AsyncOpenAI
from faiss_search import get_chunks_by_latin_name

client = AsyncOpenAI()

async def get_care_card_html(latin_name: str) -> str:
    try:
        # 1. Получение релевантных чанков
        chunks = get_chunks_by_latin_name(latin_name, top_k=100)
        if not chunks:
            return f"❌ Не найдено информации по: {latin_name}"

        texts_joined = "\n\n".join(chunks)

        # 2. Формирование промта
        prompt = f"""
На основе приведённых текстов сформируй подробную карточку ухода за растением "{latin_name}".

Требования:
– Укажи русское и латинское название
– Сформируй разделы: Свет, Полив, Температура, Почва, Удобрения, Пересадка, Размножение, Болезни, Особенности
– Используй точные данные из текста: градусы, интервалы, конкретные советы
– Если каких-то разделов нет — не придумывай
– Оформи как Telegram-сообщение: короткие абзацы, списки, структурировано

Тексты:
{texts_joined}
"""

        # 3. Вызов GPT
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        result = response.choices[0].message.content
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"❌ Ошибка при генерации карточки: {e}")
        return f"<b>Ошибка обработки карточки:</b>\n\n<pre>{html.escape(str(e))}</pre>"

async def handle_care_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle care button callbacks."""
    query = update.callback_query
    await query.answer()
    latin_name = query.data.split(":", 1)[1]
    result = await get_care_card_html(latin_name)
    if result is None:
        await query.message.reply_text(
            "❌ Ошибка при получении карточки ухода.",
            parse_mode="HTML",
        )
    elif isinstance(result, dict):
        msg = "❌ Ошибка при получении карточки ухода."
        if DEBUG_GPT and result.get("raw"):
            msg += f"\n\nRAW:\n{result['raw']}"
        await query.message.reply_text(
            msg,
            parse_mode="HTML",
        )
    else:
        await query.message.reply_text(
            result,
            parse_mode="HTML",
        )

# --- Обработка текстовых кнопок
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "ℹ️ О проекте":
        await update.message.reply_text(
            """🌿 О проекте: GreenCore

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
📬 Связь: @veryhappyEpta""",
            parse_mode="HTML",
        )
    elif text == "📢 Канал":
        await update.message.reply_text(
            "Наш канал: https://t.me/BOTanikPlants",
            parse_mode="HTML",
        )
    elif text == "📘 Инфо":
        await update.message.reply_text(
            """📘 Как пользоваться ботом GreenCore

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

📬 Есть идеи или предложения? Пиши: @veryhappyEpta""",
            parse_mode="HTML",
        )

# --- Хендлеры
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_handler(CallbackQueryHandler(handle_care_button))
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
