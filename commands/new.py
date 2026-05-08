from telegram import Update
from telegram.ext import ContextTypes

from game import new_game, get_game, MAX_GUESSES


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE, word_len: int):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id

    state = get_game(chat_id, thread_id)

    if state and state.active:
        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text="Game already running. Use /end first."
        )
        return

    new_game(chat_id, thread_id, word_len)

    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=(
            f"🎮 <b>{word_len}-letter WordSeek started!</b>\n"
            f"🧠 You have {MAX_GUESSES} guesses.\n\n"
            f"Start guessing a {word_len}-letter word."
        ),
        parse_mode="HTML"
    )


# /new → show menu
async def new(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id

    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=(
            "🎮 <b>Start a new WordSeek game</b>\n\n"
            "Choose word length:\n\n"
            "🔹 /new4  — 4 letter\n"
            "🔹 /new5  — 5 letter\n"
            "🔹 /new6  — 6 letter\n"
            "🔹 /new7  — 7 letter"
        ),
        parse_mode="HTML"
    )


async def new4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_game(update, context, 4)


async def new5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_game(update, context, 5)


async def new6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_game(update, context, 6)


async def new7(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_game(update, context, 7)