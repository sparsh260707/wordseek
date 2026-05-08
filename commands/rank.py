from telegram import Update
from telegram.ext import ContextTypes

from database import (
    get_global_leaderboard,
    get_chat_leaderboard,
    get_user
)


# ---------------- FIND RANK ----------------

def find_rank(user_id, leaderboard):
    for index, user in enumerate(leaderboard, start=1):
        if user["_id"] == user_id:
            return index
    return None


# ---------------- COMMAND ----------------

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # If replying to someone → show their rank
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    else:
        target_user = update.effective_user

    user_id = target_user.id
    chat_id = update.effective_chat.id

    user_data = get_user(user_id)

    if not user_data:
        await update.message.reply_text("No stats found yet.")
        return

    # Global leaderboard
    global_lb = get_global_leaderboard("all", limit=1000)
    global_rank = find_rank(user_id, global_lb)

    # Chat leaderboard
    chat_lb = get_chat_leaderboard(chat_id, "all", limit=1000)
    chat_rank = find_rank(user_id, chat_lb)

    global_points = user_data.get("global_points", 0)
    chat_points = user_data.get("chat_points", {}).get(str(chat_id), 0)
    total_wins = user_data.get("wins", 0)
    total_games = user_data.get("games", 0)

    text = (
        f"📊 <b>{target_user.first_name}'s Stats</b>\n\n"
        f"🌍 Global Rank: <b>{global_rank if global_rank else 'Unranked'}</b>\n"
        f"💬 Chat Rank: <b>{chat_rank if chat_rank else 'Unranked'}</b>\n\n"
        f"🏆 Global Points: <b>{global_points}</b>\n"
        f"💬 Chat Points: <b>{chat_points}</b>\n\n"
        f"🎯 Wins: <b>{total_wins}</b>\n"
        f"🎮 Games Played: <b>{total_games}</b>"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )