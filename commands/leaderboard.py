from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
import html

from database import (
    get_global_leaderboard,
    get_chat_leaderboard
)

# ==================================================
# FORMATTER
# ==================================================

def format_leaderboard(users, scope="global", period="all", chat_id=None):
    text = ""

    field_map = {
        "today": "daily_points",
        "week": "weekly_points",
        "month": "monthly_points",
        "year": "yearly_points",
        "all": "global_points"
    }

    for i, user in enumerate(users):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."

        if scope == "chat":
            pts = user.get("chat_points", {}).get(str(chat_id), 0)
        else:
            field = field_map.get(period, "global_points")
            pts = user.get(field, 0)

        name = html.escape(user.get("username", "User"))
        user_id = user["_id"]

        clickable = f"<a href='tg://user?id={user_id}'>{name}</a>"

        text += f"{medal} {clickable} — <b>{pts} pts</b>\n"

    return text if text else "No data yet."


# ==================================================
# FIND RANK
# ==================================================

def find_rank(user_id, users):
    for i, user in enumerate(users, start=1):
        if user["_id"] == user_id:
            return i
    return None


# ==================================================
# KEYBOARD
# ==================================================

def build_keyboard(scope="global", period="all"):

    def scope_btn(label, btn_scope):
        active = scope == btn_scope
        text = f"🔵 {label}" if active else label
        return InlineKeyboardButton(text, callback_data=f"lb_{btn_scope}_{period}")

    def period_btn(label, btn_period):
        active = period == btn_period
        text = f"🔹 {label}" if active else label
        return InlineKeyboardButton(text, callback_data=f"lb_{scope}_{btn_period}")

    return InlineKeyboardMarkup([
        [
            scope_btn("Global", "global"),
            scope_btn("« This chat »", "chat")
        ],
        [
            period_btn("Today", "today"),
            period_btn("This week", "week"),
            period_btn("This month", "month"),
        ],
        [
            period_btn("This year", "year"),
            period_btn("All time", "all"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"lb_{scope}_{period}")
        ],
        [
            InlineKeyboardButton("📢 Updates", url="https://t.me/wordsixneteork"),
            InlineKeyboardButton("💬 Discussion", url="https://t.me/sixletterword")
        ]
    ])


# ==================================================
# MAIN COMMAND
# ==================================================

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    users = get_global_leaderboard("all", limit=16)

    title = "🏆 <b>GLOBAL LEADERBOARD</b>\n<code>All Time</code>\n\n"
    body = format_leaderboard(users, "global", "all")

    await update.message.reply_text(
        title + body,
        parse_mode="HTML",
        reply_markup=build_keyboard("global", "all"),
        disable_web_page_preview=True
    )


# ==================================================
# CALLBACK HANDLER
# ==================================================

async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer(cache_time=1)

    chat_id = query.message.chat.id
    user_id = query.from_user.id
    data = query.data

    parts = data.split("_")
    if len(parts) != 3:
        return

    _, scope, period = parts

    if scope == "global":
        users = get_global_leaderboard(period, limit=16)
        title = f"🏆 <b>GLOBAL LEADERBOARD</b>\n<code>{period.title()}</code>\n\n"
        body = format_leaderboard(users, "global", period)
        rank = find_rank(user_id, users)

    elif scope == "chat":
        users = get_chat_leaderboard(chat_id, period, limit=16)
        title = f"🏆 <b>THIS CHAT LEADERBOARD</b>\n<code>{period.title()}</code>\n\n"
        body = format_leaderboard(users, "chat", period, chat_id)
        rank = find_rank(user_id, users)

    else:
        return

    footer = f"\n━━━━━━━━━━━━\n👤 Your Rank: <b>{rank}</b>" if rank else ""

    new_text = title + body + footer

    try:
        await query.message.edit_text(
            new_text,
            parse_mode="HTML",
            reply_markup=build_keyboard(scope, period),
            disable_web_page_preview=True
        )
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise