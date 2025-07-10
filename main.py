import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import (
    Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
)
from telegram.error import TelegramError
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from service import get_plant_data, format_plant_info_base, format_plant_info_extended, get_bot_info
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)
app = FastAPI()

dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

def start(update: Update, context):
    user = update.effective_user
    message = f"Привет, {user.first_name or 'садовод'}! Отправь название растения, чтобы получить карточку ухода."
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

def handle_message(update: Update, context):
    query = update.message.text.strip()
    plant = get_plant_data(query)

    if plant:
        info_text = format_plant_info_base(plant)
        image_url = f"https://tofik-san.github.io/helpPlantsBot/images/{plant['image']}"
        keyboard = [[InlineKeyboardButton("📄 Статья", callback_data=f"extended_{plant['id']}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=image_url,
            caption=info_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="🌱 Растение не найдено. Попробуйте другое название.")

def handle_callback(update: Update, context):
    query = update.callback_query
    data = query.data

    if data.startswith("extended_"):
        plant_id = data.replace("extended_", "")
        plant = get_plant_data(plant_id, by_id=True)

        if plant:
            extended_info = format_plant_info_extended(plant)
            query.message.reply_text(extended_info, parse_mode=ParseMode.HTML)
        else:
            query.message.reply_text("❌ Не удалось найти информацию.")

    query.answer()

def error_handler(update: object, context):
    logger.error(msg="Ошибка при обработке обновления:", exc_info=context.error)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, bot)
    dispatcher.process_update(update)
    return JSONResponse(content={"ok": True})

@app.get("/")
def root():
    return {"message": "helpPlantsBot работает!"}

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
dispatcher.add_handler(CallbackQueryHandler(handle_callback))
dispatcher.add_error_handler(error_handler)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
