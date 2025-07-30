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
from service import identify_plant, generate_care_card
from limit_checker import check_and_increment_limit

# --- Конфиги
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# --- Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class _TokenFilter(logging.Filter):
    def __init__(self, token: str) -> None:
        super().__init__()
        self.token = token or ""

    def filter(self, record: logging.LogRecord) -> bool:
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
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpx").propagate = False

# --- Telegram + FastAPI
app = FastAPI()
application = Application.builder().token(TOKEN).build()
app_state_ready = False
user_last_request = {}
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
        reply_markup=reply_markup,
        parse_mode="HTML",
    )

# --- Обработка фото
# --- Обработка фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        now = datetime.utcnow()

        # --- Защита от альбомов
        if update.message.media_group_id:
            await update.message.reply_text("📸 Отправьте, пожалуйста, только одно фото за раз.", parse_mode="HTML")
            return

        # --- Антиспам 15 сек
        last_time = user_last_request.get(user_id)
        if last_time and (now - last_time).total_seconds() < 15:
            await update.message.reply_text("⏱ Подождите 15 секунд перед новой попыткой.", parse_mode="HTML")
            return
        user_last_request[user_id] = now

        # --- Ограничение размера фото
        photo = update.message.photo[-1]
        if photo.file_size and photo.file_size > 5 * 1024 * 1024:
            await update.message.reply_text("❌ Фото слишком большое. Попробуйте другое.", parse_mode="HTML")
            return

        # --- Скачивание фото
        file = await context.bot.get_file(photo.file_id)
        temp_path = "temp/plant.jpg"
        await file.download_to_drive(custom_path=temp_path)

        # --- Проверка формата изображения
        img_type = imghdr.what(temp_path)
        if img_type not in ("jpeg", "png"):
            await update.message.reply_text("❌ Не удалось распознать формат. Попробуйте другое фото.", parse_mode="HTML")
            return

        # --- Лимит по пользователю
        if not await check_and_increment_limit(user_id):
            await update.message.reply_text("🚫 Лимит на сегодня исчерпан. Попробуйте завтра.", parse_mode="HTML")
            return

        # --- Распознавание
        await update.message.reply_text("Распознаю растение…", parse_mode="HTML")
        result = await identify_plant(temp_path)

        if not result:
            logger.warning(f"[handle_photo] identify_plant вернул None для user_id={user_id}")
            await update.message.reply_text("❌ Не удалось распознать растение. Попробуйте другое фото.", parse_mode="HTML")
            return

        suggestions = result.get("suggestions", [])
        if not suggestions:
            logger.warning(f"[handle_photo] Пустой suggestions. Full result: {result}")
            await update.message.reply_text("❌ Не удалось распознать растение.", parse_mode="HTML")
            return

        top = suggestions[0]
        name = top.get("plant_name", "неизвестно")
        prob = round(top.get("probability", 0) * 100, 2)
        details = top.get("plant_details", {})
        common_names = details.get("common_names", [])
        russian_name = common_names[0] if common_names else name

        is_plant_prob = result.get("is_plant_probability", 0)
        if is_plant_prob >= 0.2:
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🧠 Уход от BOTanika", callback_data=f"care:{name}")]]
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🌱 Похоже, это: {russian_name} / {name} ({prob}%)",
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Не удалось распознать растение. Попробуйте другое фото.",
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"[handle_photo] Ошибка: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("🚫 Ошибка при распознавании растения. Попробуйте позже.", parse_mode="HTML")


# --- Обработка кнопки ухода
from telegram.error import BadRequest
import time

async def handle_care_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    latin_name = query.data.split(":", 1)[1]

    # ⏱ Старт таймера
    start_time = time.time()

    try:
        result = await generate_care_card(latin_name)
    except Exception as e:
        logger.error(f"[handle_care_button] Ошибка генерации карточки: {e}\n{traceback.format_exc()}")
        await query.message.reply_text("❌ Ошибка при генерации карточки ухода.", parse_mode="HTML")
        return

    # 🕒 Пытаемся ответить на query
    try:
        await query.answer()
    except BadRequest as e:
        if "query is too old" in str(e).lower():
            logger.warning(f"[handle_care_button] Просроченный callback: {e}")
        else:
            raise

    # 🧾 Ответ пользователю
    if not result:
        await query.message.reply_text("❌ Не удалось сформировать карточку ухода.", parse_mode="HTML")
    else:
        await query.message.reply_text(result, parse_mode="HTML")

    logger.info(f"[handle_care_button] Время генерации: {time.time() - start_time:.2f} сек.")


# --- Обработка кнопок меню
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "ℹ️ О проекте":
        await update.message.reply_text("Описание проекта...", parse_mode="HTML")
    elif text == "📢 Канал":
        await update.message.reply_text("Наш канал: https://t.me/BOTanikPlants", parse_mode="HTML")
    elif text == "📘 Инфо":
        await update.message.reply_text("Инструкция по использованию...", parse_mode="HTML")

# --- Хендлеры
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_handler(CallbackQueryHandler(handle_care_button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
