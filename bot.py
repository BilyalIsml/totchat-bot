import os
import logging
import requests

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "google/gemma-2-9b-it"

# ---------- ЛОГИ ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("🚀 TotChat bot starting...")

# ---------- ОБРАБОТКА СООБЩЕНИЙ ----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.message.from_user.id

    logging.info(f"User {user_id} sent: {user_text}")

    try:
        response = requests.post(
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
                        "content": "Ты TotChat — умный ИИ-помощник. Отвечай логично, понятно и полезно."
                    },
                    {"role": "user", "content": user_text}
                ]
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()
        answer = data["choices"][0]["message"]["content"]

        await update.message.reply_text(answer)

    except Exception as e:
        logging.error(f"ERROR for user {user_id}: {e}")
        await update.message.reply_text(
            "⚠️ Произошла временная ошибка. Попробуй чуть позже."
        )

# ---------- ЗАПУСК ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
app.run_polling()
