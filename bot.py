import os
import logging
import time
import requests
import asyncio
import json

from telegram import Update, ReplyKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from telegram.error import Conflict

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# 🔥 более сильная модель
MODEL = "openai/gpt-4o-mini"

USERS_FILE = "users.json"

# ---------- ЛОГИ ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.info("🚀 ChatGPT bot starting...")

# ---------- ЛИМИТ СООБЩЕНИЙ ----------
user_last_time = {}
MESSAGE_COOLDOWN = 5

def can_send(user_id):
    now = time.time()
    last = user_last_time.get(user_id, 0)
    if now - last < MESSAGE_COOLDOWN:
        return False
    user_last_time[user_id] = now
    return True

# ---------- ЗАГРУЗКА ПОЛЬЗОВАТЕЛЕЙ ----------
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        users = set(json.load(f))
else:
    users = set()

def add_user(user_id):
    if user_id not in users:
        users.add(user_id)
        with open(USERS_FILE, "w") as f:
            json.dump(list(users), f)

# ---------- КЛАВИАТУРА ----------
keyboard = ReplyKeyboardMarkup(
    [["/start", "/help"], ["/tp"]],
    resize_keyboard=True
)

# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    add_user(user_id)

    user_name = update.message.from_user.first_name

    await update.message.reply_text(
        f"🔥 Привет, {user_name}! Я *ChatGPT Helper* — твой ИИ-помощник.\n\n"
        f"👥 Всего пользователей: {len(users)}\n\n"
        "💡 Напиши любой вопрос — я постараюсь помочь.\n"
        "Используй кнопки ниже или команды /help, /tp",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

# ---------- /help ----------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ Доступные команды:\n"
        "/start — Главное меню\n"
        "/help — Помощь\n"
        "/tp — Спросить ИИ\n\n"
        "Просто напиши свой вопрос — ChatGPT ответит!",
        parse_mode="Markdown"
    )

# ---------- /tp ----------
async def tp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await help_command(update, context)

# ---------- ОБРАБОТКА СООБЩЕНИЙ ----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text.strip()

    # 🔥 защита от спама
    if not can_send(user_id):
        await update.message.reply_text("⏳ Подожди немного перед следующим сообщением.")
        return

    # 🔥 фильтр коротких сообщений
    if len(user_text) < 2:
        await update.message.reply_text("💬 Напиши более подробный вопрос 🙂")
        return

    logging.info(f"User {user_id} sent: {user_text}")

    try:
        thinking = await update.message.reply_text("💭 Думаю...")
        await asyncio.sleep(0.8)

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "temperature": 0.4,
                "max_tokens": 800,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Ты ChatGPT Helper — точный и полезный ИИ-ассистент. "
                            "Отвечай кратко, по делу и без выдумок. "
                            "Если не знаешь ответ — честно скажи об этом. "
                            "Говори на языке пользователя."
                        )
                    },
                    {"role": "user", "content": user_text}
                ]
            },
            timeout=30
        )

        response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"]

        await thinking.edit_text(f"💡 {answer}", parse_mode="Markdown")

    except Exception as e:
        logging.error(f"ERROR for user {user_id}: {e}")
        await update.message.reply_text(
            "⚠️ Произошла временная ошибка. Попробуй чуть позже."
        )

# ---------- ЗАПУСК ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()

# ---------- МЕНЮ КОМАНД ----------
commands = [
    BotCommand("start", "🏠 Главное меню"),
    BotCommand("help", "❓ Помощь"),
    BotCommand("tp", "💭 Спросить ИИ")
]
app.bot.set_my_commands(commands)

# ---------- РЕГИСТРАЦИЯ ----------
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("tp", tp_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

# ---------- ЗАПУСК ----------
try:
    app.run_polling()
except Conflict:
    logging.warning("🚨 Конфликт polling. Старый бот был завершён.")
