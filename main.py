from fastapi import FastAPI, Request
import logging
import json

app = FastAPI()
logging.basicConfig(level=logging.INFO)

@app.post("/webhook")
async def webhook(req: Request):
    try:
        data = await req.json()
        logging.info(f"📩 Получен запрос: {json.dumps(data, ensure_ascii=False)}")

        message = data.get("message")
        if not message:
            logging.warning("⚠️ Нет поля 'message' в payload")
            return {"ok": True}

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        logging.info(f"🗣 Пользователь: {chat_id} → {text}")
        # Здесь вставь свою основную обработку текста и ответ боту, если нужно

    except Exception as e:
        logging.exception("❌ Ошибка в обработчике webhook")

    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
