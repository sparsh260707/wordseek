from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
import html

from database import (
    get_global_leaderboard,
    get_chat_leaderboard,
    get_user_word_scores  # You'll need to implement this based on your schema
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
# WORD LENGTH STATS FORMATTER
# ==================================================

async def show_word_length_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, word_length: int):
    """Fetch and display scores for specific word length"""
    # You need to implement get_user_word_scores based on your database schema
    # This is an example implementation
    score_data = await get_user_word_scores(user_id, word_length)
    
    if score_data:
        text = f"📊 <b>Word Length: {word_length} Letters</b>\n\n"
        text += f"Total words found: <b>{score_data.get('total_words', 0)}</b>\n"
        text += f"Total score: <b>{score_data.get('total_score', 0)} pts</b>\n\n"
        
        if score_data.get('recent_words'):
            text += "📝 Recent words:\n"
            for word, score in list(score_data['recent_words'].items())[:10]:
                text += f"• {word} — {score} pts\n"
    else:
        text = f"📊 <b>Word Length: {word_length} Letters</b>\n\n"
        text += "No words found for this length yet!"
    
    return text


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

def build_keyboard(scope="global", period="all", show_word_buttons=False):
    buttons = []
    
    # Leaderboard navigation buttons
    def scope_btn(label, btn_scope):
        active = scope == btn_scope
        text = f"🔵 {label}" if active else label
        return InlineKeyboardButton(text, callback_data=f"lb_{btn_scope}_{period}")
    
    def period_btn(label, btn_period):
        active = period == btn_period
        text = f"🔹 {label}" if active else label
        return InlineKeyboardButton(text, callback_data=f"lb_{scope}_{btn_period}")
    
    # Row 1: Scope selection
    buttons.append([
        scope_btn("Global", "global"),
        scope_btn("« This chat »", "chat")
    ])
    
    # Row 2: Period selection (daily, weekly, monthly)
    buttons.append([
        period_btn("Today", "today"),
        period_btn("This week", "week"),
        period_btn("This month", "month"),
    ])
    
    # Row 3: Period selection (yearly, all time)
    buttons.append([
        period_btn("This year", "year"),
        period_btn("All time", "all"),
    ])
    
    # Row 4: Refresh button
    buttons.append([
        InlineKeyboardButton("🔄 Refresh", callback_data=f"lb_{scope}_{period}")
    ])
    
    # Row 5: Word length buttons (NEW)
    buttons.append([
        InlineKeyboardButton("🔤 4 Letter Scores", callback_data="wordlen_4"),
        InlineKeyboardButton("🔤 5 Letter Scores", callback_data="wordlen_5"),
        InlineKeyboardButton("🔤 6 Letter Scores", callback_data="wordlen_6"),
        InlineKeyboardButton("🔤 7 Letter Scores", callback_data="wordlen_7"),
    ])
    
    # Row 6: Back to leaderboard button (only shown when viewing word stats)
    if show_word_buttons:
        buttons.append([
            InlineKeyboardButton("◀️ Back to Leaderboard", callback_data=f"lb_{scope}_{period}")
        ])
    
    # Row 7: Social links
    buttons.append([
        InlineKeyboardButton("📢 Updates", url="https://t.me/wordsixneteork"),
        InlineKeyboardButton("💬 Discussion", url="https://t.me/sixletterword")
    ])
    
    return InlineKeyboardMarkup(buttons)


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
        reply_markup=build_keyboard("global", "all", show_word_buttons=False),
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
    
    # Handle word length score buttons
    if data.startswith("wordlen_"):
        word_length = int(data.split("_")[1])
        
        # Get current state from callback data or store in context
        # For simplicity, we'll extract from the current message if possible
        # Or we can store the last scope/period in context.user_data
        current_scope = context.user_data.get('last_scope', 'global')
        current_period = context.user_data.get('last_period', 'all')
        
        # Show word length statistics
        stats_text = await show_word_length_stats(update, context, user_id, word_length)
        
        await query.message.edit_text(
            stats_text,
            parse_mode="HTML",
            reply_markup=build_keyboard(current_scope, current_period, show_word_buttons=True),
            disable_web_page_preview=True
        )
        return
    
    # Handle leaderboard navigation
    parts = data.split("_")
    if len(parts) != 3:
        return
    
    _, scope, period = parts
    
    # Store current state for word length buttons
    context.user_data['last_scope'] = scope
    context.user_data['last_period'] = period
    
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
            reply_markup=build_keyboard(scope, period, show_word_buttons=False),
            disable_web_page_preview=True
        )
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise
