import os
import logging
import time
import requests
import asyncio

from telegram import Update, ReplyKeyboardMarkup, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from telegram.error import Conflict

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

# ---------- ЛИМИТ СООБЩЕНИЙ ----------
user_last_time = {}
MESSAGE_COOLDOWN = 5  # секунд между сообщениями

def can_send(user_id):
    now = time.time()
    last = user_last_time.get(user_id, 0)
    if now - last < MESSAGE_COOLDOWN:
        return False
    user_last_time[user_id] = now
    return True

# ---------- КРАСИВОЕ МЕНЮ ----------
keyboard = ReplyKeyboardMarkup(
    [["/start", "/help"], ["/tp"]],
    resize_keyboard=True
)

# ---------- КОМАНДЫ ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"🔥 Привет, {user_name}! Я *TotChat* — твой ИИ-помощник.\n\n"
        "💡 Напиши мне любой вопрос, и я дам ответ.\n"
        "Используй кнопки ниже или команды /help, /tp",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ Доступные команды:\n"
        "/start — приветствие и меню\n"
        "/help или /tp — справка\n\n"
        "Просто напиши свой вопрос, и я отвечу!",
        parse_mode="Markdown"
    )

# ---------- ОБРАБОТКА СООБЩЕНИЙ С “💭 думаю…” ----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text

    if not can_send(user_id):
        await update.message.reply_text("⏳ Подожди немного перед следующим сообщением.")
        return

    logging.info(f"User {user_id} sent: {user_text}")

    try:
        # Отправляем сообщение "думаю"
        thinking = await update.message.reply_text("💭 Думаю...")
        await asyncio.sleep(1)  # пауза, чтобы выглядело живо

        # Запрос к OpenRouter
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

        # Редактируем сообщение “думаю” на реальный ответ
        await thinking.edit_text(f"💡 {answer}", parse_mode="Markdown")

    except Exception as e:
        logging.error(f"ERROR for user {user_id}: {e}")
        await update.message.reply_text(
            "⚠️ Произошла временная ошибка. Попробуй чуть позже."
        )

# ---------- ЗАПУСК ----------
bot_instance = Bot(BOT_TOKEN)
bot_instance.delete_webhook()
logging.info("✅ Webhook removed (если был)")

app = ApplicationBuilder().token(BOT_TOKEN).build()

# Команды
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("tp", help_command))

# Сообщения
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

# Запуск с обработкой Conflict
try:
    app.run_polling()
except Conflict:
    logging.warning("🚨 Конфликт polling. Старый бот был завершён.")
