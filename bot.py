import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "google/gemma-2-9b-it"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "Ты TotChat — умный ИИ-помощник. Отвечай понятно и полезно."},
                {"role": "user", "content": user_text}
            ]
        }
    )

    answer = r.json()["choices"][0]["message"]["content"]
    await update.message.reply_text(answer)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
app.run_polling()

