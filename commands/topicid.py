from telegram import Update
from telegram.ext import ContextTypes

async def topicid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    thread_id = update.message.message_thread_id
    await update.message.reply_text(f"THREAD ID: {thread_id}")