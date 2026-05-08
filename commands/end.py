from telegram import Update
from telegram.ext import ContextTypes

from game import get_game, end_game


async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id

    state = get_game(chat_id, thread_id)

    if not state or not state.active:
        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text="No active game in this topic."
        )
        return

    correct_word = state.answer.upper()
    word_len = state.word_len

    end_game(chat_id, thread_id)

    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=(
            f"🛑 <b>{word_len}-letter game ended.</b>\n\n"
            f"🎯 Correct Word: <b>{correct_word}</b>\n\n"
            f"Start again with /new{word_len}"
        ),
        parse_mode="HTML"
    )


# /end → show menu
async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id

    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=(
            "🛑 <b>End WordSeek Game</b>\n\n"
            "Choose which game to end:\n\n"
            "🔹 /end4 — End 4 letter game\n"
            "🔹 /end5 — End 5 letter game\n"
            "🔹 /end6 — End 6 letter game\n"
            "🔹 /end7 — End 7 letter game"
        ),
        parse_mode="HTML"
    )


async def end4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_game(update, context)


async def end5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_game(update, context)


async def end6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_game(update, context)


async def end7(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_game(update, context)