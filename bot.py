import os
import logging
import time
import asyncio
import aiohttp

from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from telegram.error import Conflict

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "google/gemma-2-9b-it"

# ---------- ЛОГИ ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
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

# ---------- КОМАНДЫ ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"🔥 Привет, {user_name}! Я *TotChat* — твой ИИ-помощник.\n\n"
        "💡 Используй меню команд (кнопка рядом с полем ввода) или просто напиши свой вопрос.",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ Доступные команды:\n"
        "/start — главное меню\n"
        "/help — справка\n"
        "/tp <текст> — спросить ИИ\n\n"
        "Просто напиши свой вопрос, и я отвечу!",
        parse_mode="Markdown"
    )

async def tos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📄 Пользовательское соглашение:\n..."
    )

async def tp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("💭 Пожалуйста, напиши вопрос после команды /tp")
        return

    user_text = " ".join(context.args)
    await handle(update, context, user_text)

# ---------- ОБРАБОТКА СООБЩЕНИЙ С “💭 думаю…” ----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text=None):
    user_id = update.message.from_user.id
    user_text = user_text or update.message.text

    if not can_send(user_id):
        await update.message.reply_text("⏳ Подожди немного перед следующим сообщением.")
        return

    logging.info(f"User {user_id} sent: {user_text}")

    try:
        # Сообщение "думаю"
        thinking = await update.message.reply_text("💭 Думаю...")
        await asyncio.sleep(0.5)  # маленькая пауза для эффекта

        # Асинхронный запрос к OpenRouter
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": "Ты TotChat — умный ИИ-помощник. Отвечай логично и понятно."},
                        {"role": "user", "content": user_text}
                    ]
                },
                timeout=30
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                answer = data["choices"][0]["message"]["content"]

        # Редактируем сообщение “думаю” на ответ
        await thinking.edit_text(f"💡 {answer}", parse_mode="Markdown")

    except Exception as e:
        logging.error(f"ERROR for user {user_id}: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка. Попробуй чуть позже.")

# ---------- ЗАПУСК БОТА ----------
bot_instance = ApplicationBuilder().token(BOT_TOKEN).build()

# Устанавливаем команды меню (Telegram встроенное меню)
commands = [
    BotCommand("start", "🏠 Главное меню"),
    BotCommand("help", "❓ Помощь"),
    BotCommand("tp", "💭 Спросить ИИ"),
    BotCommand("tos", "📄 Пользовательское соглашение")
]
bot_instance.bot.set_my_commands(commands)

# Регистрируем команды
bot_instance.add_handler(CommandHandler("start", start))
bot_instance.add_handler(CommandHandler("help", help_command))
bot_instance.add_handler(CommandHandler("tp", tp_command))
bot_instance.add_handler(CommandHandler("tos", tos_command))

# Сообщения без команд
bot_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

# Запуск с обработкой Conflict
try:
    bot_instance.run_polling()
except Conflict:
    logging.warning("🚨 Конфликт polling. Старый бот был завершён.")
