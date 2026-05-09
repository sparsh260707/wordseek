from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
import html

from database import (
    get_global_leaderboard,
    get_chat_leaderboard,
    get_user  # Added this import
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
    user = get_user(user_id)
    
    if not user or "words" not in user:
        text = f"📊 <b>Word Length: {word_length} Letters</b>\n\n"
        text += "No words found for this length yet!\n"
        text += "Play the game to start collecting words."
        return text
    
    # Get all words from user's history
    words_data = user.get("words", {})
    
    # Filter words by length
    words_of_length = {}
    total_score = 0
    
    for word, data in words_data.items():
        if len(word) == word_length:
            score = data.get("score", 0)
            words_of_length[word] = {
                "score": score,
                "timestamp": data.get("timestamp", datetime.utcnow())
            }
            total_score += score
    
    if not words_of_length:
        text = f"📊 <b>Word Length: {word_length} Letters</b>\n\n"
        text += f"No {word_length}-letter words found yet!\n"
        text += "Keep playing to discover new words."
        return text
    
    # Sort by timestamp (most recent first) for recent words
    sorted_words = sorted(
        words_of_length.items(),
        key=lambda x: x[1]["timestamp"],
        reverse=True
    )
    
    # Calculate statistics
    unique_words = len(words_of_length)
    avg_score = total_score / unique_words if unique_words > 0 else 0
    
    # Format the response
    text = f"📊 <b>Word Length: {word_length} Letters</b>\n\n"
    text += f"🔤 Unique words found: <b>{unique_words}</b>\n"
    text += f"⭐ Total score: <b>{total_score} pts</b>\n"
    text += f"📈 Average per word: <b>{avg_score:.1f} pts</b>\n\n"
    
    text += "📝 <b>Most Recent Words:</b>\n"
    for word, data in sorted_words[:10]:
        text += f"• <code>{word}</code> — {data['score']} pts\n"
    
    # Add highest scoring word if available
    highest_score_word = max(words_of_length.items(), key=lambda x: x[1]["score"])
    if highest_score_word:
        text += f"\n🏆 <b>Highest scoring:</b> <code>{highest_score_word[0]}</code> — {highest_score_word[1]['score']} pts"
    
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

def build_keyboard(scope="global", period="all", show_word_buttons=False, current_word_len=None):
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
    
    # Row 5: Word length buttons
    word_buttons = []
    for length in [4, 5, 6, 7]:
        is_active = current_word_len == length
        emoji = "🔵" if is_active else "⚪"
        word_buttons.append(
            InlineKeyboardButton(
                f"{emoji} {length} Letters", 
                callback_data=f"wordlen_{length}"
            )
        )
    buttons.append(word_buttons)
    
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
    
    # Initialize user data for word length buttons
    if 'last_scope' not in context.user_data:
        context.user_data['last_scope'] = 'global'
    if 'last_period' not in context.user_data:
        context.user_data['last_period'] = 'all'
    
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
        
        # Get current state from user_data
        current_scope = context.user_data.get('last_scope', 'global')
        current_period = context.user_data.get('last_period', 'all')
        
        # Show word length statistics
        stats_text = await show_word_length_stats(update, context, user_id, word_length)
        
        # Add header
        header = f"🔍 <b>Your {word_length}-Letter Word Stats</b>\n\n"
        
        await query.message.edit_text(
            header + stats_text,
            parse_mode="HTML",
            reply_markup=build_keyboard(
                current_scope, 
                current_period, 
                show_word_buttons=True,
                current_word_len=word_length
            ),
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
