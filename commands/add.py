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


def extract_list(data):
    """Support both list JSON and {'words':[]} JSON"""
    if isinstance(data, dict) and "words" in data:
        return data["words"], data
    return data, None


async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = update.effective_user.id

    # Admin check
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admin can add words.")
        return

    word = None

    # /add word
    if context.args:
        word = context.args[0].strip().lower()

    # reply add
    elif update.message.reply_to_message and update.message.reply_to_message.text:
        word = update.message.reply_to_message.text.strip().lower()

    if not word:
        await update.message.reply_text(
            "Usage:\n/add word\nor reply to a word with /add"
        )
        return

    if not word.isalpha():
        await update.message.reply_text("Only alphabet words allowed.")
        return

    word_len = len(word)

    if word_len not in FILE_MAP:
        await update.message.reply_text("Only 4,5,6,7 letter words allowed.")
        return

    answers_file = os.path.join(WORDS_DIR, FILE_MAP[word_len][0])
    allowed_file = os.path.join(WORDS_DIR, FILE_MAP[word_len][1])

    try:
        with open(allowed_file, "r", encoding="utf-8") as f:
            allowed_raw = json.load(f)

        with open(answers_file, "r", encoding="utf-8") as f:
            answers_raw = json.load(f)

        allowed, allowed_dict = extract_list(allowed_raw)
        answers, answers_dict = extract_list(answers_raw)

    except Exception:
        await update.message.reply_text("Error reading word files.")
        return

    if word in allowed:
        await update.message.reply_text("Word already exists.")
        return

    allowed.append(word)
    answers.append(word)

    # update count if exists
    if answers_dict and "count" in answers_dict:
        answers_dict["count"] = len(answers)

    if allowed_dict and "count" in allowed_dict:
        allowed_dict["count"] = len(allowed)

    try:

        # write answers
        if answers_dict:
            answers_dict["words"] = answers
            data = answers_dict
        else:
            data = answers

        with open(answers_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # write allowed
        if allowed_dict:
            allowed_dict["words"] = allowed
            data = allowed_dict
        else:
            data = allowed

        with open(allowed_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # clear cache
        if word_len in WORD_CACHE:
            del WORD_CACHE[word_len]

        await update.message.reply_text(
            f"✅ Added {word.upper()} ({word_len} letters)"
        )

    except Exception:
        await update.message.reply_text("Error writing word file.")