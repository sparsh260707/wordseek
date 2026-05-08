from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import ContextTypes

# ---------------- SETTINGS ----------------

BOT_USERNAME = "@WordleGameProobot"  # change if needed

IMAGE_URL = "https://graph.org/file/32981621f9dee50578e3f-e4f6630687ca8cb11a.jpg"

START_TEXT = """
<b>Welcome to WordSix!</b>

A fun and competitive 6-letter Wordle-style game you can play directly on Telegram.

<b>Quick Start:</b>
• Use /new to start a new game
• Use /end to stop the current game
• Add me to a group to play with friends
• Press Help for full instructions

Ready to test your word skills? Let's play!
"""

HELP_TEXT = """
<b>WordSix – Full Guide</b>

This is a 6-letter Wordle-style game.

🟩 Green – Correct letter, correct position
🟨 Yellow – Correct letter, wrong position
🟥 Red – Letter not in word

<b>Commands:</b>

• /new – Start a new game
• /end – End current game
• /start – Show welcome panel

<b>How to Play:</b>

1. Type any valid 6-letter word.
2. The bot will return colored boxes.
3. You have 30 guesses.
4. Guess the correct word to win.

Good luck and have fun!
"""

# ---------------- START COMMAND ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    thread_id = update.message.message_thread_id

    keyboard = [
        [InlineKeyboardButton(
            "Add me to your Group",
            url=f"https://t.me/{BOT_USERNAME}?startgroup=true"
        )],
        [
            InlineKeyboardButton("Updates", url="https://t.me/AURA_NETWORKS"),
            InlineKeyboardButton("Help", callback_data="help_panel"),
            InlineKeyboardButton("Discussion", url="https://t.me/AURA_NETWORKS")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # PRIVATE CHAT
    if chat.type == "private":
        await context.bot.send_photo(
            chat_id=chat.id,
            photo=IMAGE_URL,
            caption=START_TEXT,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    # GROUP / TOPIC
    else:
        await context.bot.send_message(
            chat_id=chat.id,
            message_thread_id=thread_id,
            text="WordSix is active!\nUse /new to start playing."
        )


# ---------------- CALLBACK HANDLER ----------------

async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    thread_id = query.message.message_thread_id

    if query.data == "help_panel":
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            message_thread_id=thread_id,
            text=HELP_TEXT,
            parse_mode="HTML"
        )
