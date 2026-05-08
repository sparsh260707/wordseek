import os
import json
from telegram import Update
from telegram.ext import ContextTypes
from dotenv import load_dotenv

from game import WORDS_DIR, FILE_MAP, WORD_CACHE

load_dotenv()

# -------- LOAD ADMIN IDS --------

ADMIN_IDS = set()
raw_ids = os.getenv("ADMIN_IDS", "")

if raw_ids:
    ADMIN_IDS = {int(x.strip()) for x in raw_ids.split(",") if x.strip().isdigit()}


async def remove_word(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = update.effective_user.id

    # 🔒 Admin check
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admin can remove words.")
        return

    word = None

    # Case 1: /remove planet
    if context.args:
        word = context.args[0].strip().lower()

    # Case 2: reply to message
    elif update.message.reply_to_message:
        if update.message.reply_to_message.text:
            word = update.message.reply_to_message.text.strip().lower()

    if not word:
        await update.message.reply_text(
            "Usage:\n/remove word\nor reply to a word with /remove"
        )
        return

    if not word.isalpha():
        await update.message.reply_text("Invalid word.")
        return

    word_len = len(word)

    if word_len not in FILE_MAP:
        await update.message.reply_text("Only 4, 5, 6 letter words allowed.")
        return

    answers_file = os.path.join(WORDS_DIR, FILE_MAP[word_len][0])
    allowed_file = os.path.join(WORDS_DIR, FILE_MAP[word_len][1])

    try:
        with open(allowed_file, "r", encoding="utf-8") as f:
            allowed = json.load(f)

        with open(answers_file, "r", encoding="utf-8") as f:
            answers = json.load(f)

    except Exception:
        await update.message.reply_text("Error reading word files.")
        return

    if word not in allowed:
        await update.message.reply_text("Word not found.")
        return

    # Remove word from lists
    if word in allowed:
        allowed.remove(word)

    if word in answers:
        answers.remove(word)

    try:
        with open(allowed_file, "w", encoding="utf-8") as f:
            json.dump(allowed, f, indent=2)

        with open(answers_file, "w", encoding="utf-8") as f:
            json.dump(answers, f, indent=2)

        # Clear cache so changes apply instantly
        if word_len in WORD_CACHE:
            del WORD_CACHE[word_len]

        await update.message.reply_text(f"❌ Removed {word.upper()}")

    except Exception:
        await update.message.reply_text("Error writing word file.")