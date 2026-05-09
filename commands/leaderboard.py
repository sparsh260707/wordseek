from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
import html
from datetime import datetime

from database import (
    get_global_leaderboard,
    get_chat_leaderboard,
    get_user,
    get_word_length_leaderboard  # New function we'll add
)

# ==================================================
# FORMATTER
# ==================================================

def format_leaderboard(users, scope="global", period="all", chat_id=None, word_length=None):
    text = ""

    if word_length:
        # For word length leaderboard
        for i, user in enumerate(users):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            
            # Points are already filtered in the query
            pts = user.get("points", 0)
            
            name = html.escape(user.get("username", "User"))
            user_id = user["_id"]
            
            clickable = f"<a href='tg://user?id={user_id}'>{name}</a>"
            text += f"{medal} {clickable} — <b>{pts} pts</b>\n"
    else:
        # Regular leaderboard
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

def build_keyboard(scope="global", period="all", word_length=None):
    buttons = []
    
    # Row 1: Scope buttons (Global and This chat)
    row1 = []
    
    # Only show scope buttons if not in word length view
    if word_length is None:
        if scope == "global":
            row1.append(InlineKeyboardButton("« Global »", callback_data=f"lb_global_{period}"))
        else:
            row1.append(InlineKeyboardButton("Global", callback_data=f"lb_global_{period}"))
        
        if scope == "chat":
            row1.append(InlineKeyboardButton("« This chat »", callback_data=f"lb_chat_{period}"))
        else:
            row1.append(InlineKeyboardButton("This chat", callback_data=f"lb_chat_{period}"))
        
        buttons.append(row1)
    
    # Row 2: Period buttons (only for regular leaderboard)
    if word_length is None:
        row2 = []
        
        if period == "today":
            row2.append(InlineKeyboardButton("« Today »", callback_data=f"lb_{scope}_today"))
        else:
            row2.append(InlineKeyboardButton("Today", callback_data=f"lb_{scope}_today"))
        
        if period == "week":
            row2.append(InlineKeyboardButton("« This week »", callback_data=f"lb_{scope}_week"))
        else:
            row2.append(InlineKeyboardButton("This week", callback_data=f"lb_{scope}_week"))
        
        if period == "month":
            row2.append(InlineKeyboardButton("« This month »", callback_data=f"lb_{scope}_month"))
        else:
            row2.append(InlineKeyboardButton("This month", callback_data=f"lb_{scope}_month"))
        
        buttons.append(row2)
        
        row3 = []
        
        if period == "year":
            row3.append(InlineKeyboardButton("« This year »", callback_data=f"lb_{scope}_year"))
        else:
            row3.append(InlineKeyboardButton("This year", callback_data=f"lb_{scope}_year"))
        
        if period == "all":
            row3.append(InlineKeyboardButton("« All time »", callback_data=f"lb_{scope}_all"))
        else:
            row3.append(InlineKeyboardButton("All time", callback_data=f"lb_{scope}_all"))
        
        buttons.append(row3)
    
    # Row 4: Word length buttons
    row4 = []
    lengths = [4, 5, 6, 7]
    
    for length in lengths:
        if word_length == length:
            # Active word length button
            row4.append(InlineKeyboardButton(f"« {length} letters »", callback_data=f"wordlen_{length}"))
        else:
            row4.append(InlineKeyboardButton(f"{length} letters", callback_data=f"wordlen_{length}"))
    
    buttons.append(row4)
    
    # Row 5: Back button (if in word length view)
    if word_length is not None:
        buttons.append([
            InlineKeyboardButton("« Back to Leaderboard »", callback_data=f"lb_{scope}_{period}")
        ])
    
    # Row 6: Social links
    row6 = [
        InlineKeyboardButton("Updates", url="https://t.me/AURA_NETWORKS"),
        InlineKeyboardButton("Donate", url="https://t.me/AURA_NETWORKS"),
        InlineKeyboardButton("Discuss", url="https://t.me/AURA_NETWORKS")
    ]
    buttons.append(row6)
    
    return InlineKeyboardMarkup(buttons)


# ==================================================
# MAIN COMMAND
# ==================================================

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = get_global_leaderboard("all", limit=16)
    
    title = "🏆 <b>GLOBAL LEADERBOARD</b>\n<code>All Time</code>\n\n"
    body = format_leaderboard(users, "global", "all")
    
    # Initialize user data
    if 'last_scope' not in context.user_data:
        context.user_data['last_scope'] = 'global'
    if 'last_period' not in context.user_data:
        context.user_data['last_period'] = 'all'
    
    await update.message.reply_text(
        title + body,
        parse_mode="HTML",
        reply_markup=build_keyboard("global", "all", word_length=None),
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
    
    # Handle word length leaderboard buttons
    if data.startswith("wordlen_"):
        word_length = int(data.split("_")[1])
        
        # Get word length leaderboard
        users = get_word_length_leaderboard(word_length, limit=16)
        
        # Get user's rank
        rank = find_rank(user_id, users)
        
        title = f"📊 <b>WORD LEADERBOARD</b>\n<code>{word_length}-Letter Words</code>\n\n"
        body = format_leaderboard(users, word_length=word_length)
        footer = f"\n━━━━━━━━━━━━\n👤 Your Rank: <b>{rank}</b>" if rank else ""
        
        new_text = title + body + footer
        
        # Store current state
        current_scope = context.user_data.get('last_scope', 'global')
        current_period = context.user_data.get('last_period', 'all')
        
        await query.message.edit_text(
            new_text,
            parse_mode="HTML",
            reply_markup=build_keyboard(current_scope, current_period, word_length=word_length),
            disable_web_page_preview=True
        )
        return
    
    # Handle leaderboard navigation
    parts = data.split("_")
    if len(parts) != 3:
        return
    
    _, scope, period = parts
    
    # Store current state
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
            reply_markup=build_keyboard(scope, period, word_length=None),
            disable_web_page_preview=True
        )
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise
