import os
import requests
import logging
from collections import defaultdict

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "google/gemma-2-9b-it"

# ---------- ЛОГИ ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------- СЧЁТЧИКИ ----------
user_requests = defaultdict(int)
total_requests = 0

# ---------- ОБРАБОТКА СООБЩЕНИЙ ----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global total_requests

    user_text = update.message.text
    user_id = update.message.from_user.id

    # считаем запросы
    user_requests[user_id] += 1
    total_requests += 1

    logging.info(
        f"User {user_id}: {user_requests[user_id]} requests | total: {total_requests}"
    )

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты TotChat — умный ИИ-помощник. Отвечай логично, ясно и полезно."
                    },
                    {"role": "user", "content": user_text}
                ]
            },
            timeout=30
        )

        r.raise_for_status()

        data = r.json()
        answer = data["choices"][0]["message"]["content"]

        await update.message.reply_text(answer)

    except Exception as e:
        logging.error(f"ERROR for user {user_id}: {e}")
        await update.message.reply_text("⚠️ Временная ошибка. Попробуй позже.")

# ---------- ЗАПУСК ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
app.run_polling()
