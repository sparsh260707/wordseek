import os
import json
import html
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes

from database import (
    reset_tournament_all,
    reset_tournament_points_only,
    join_tournament,
    get_tournament_leaderboard,
    set_double_points_prize,
)

load_dotenv()

SUPPORT_GROUP_ID = int(os.getenv("SUPPORT_GROUP_ID", "0"))
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "tournament_state.json")

STAGES = {
    1: ("normal",  None),
    2: ("quarter", 16),
    3: ("semi",     8),
    4: ("final",    4),
}


# ==================================================
# STATE HANDLING
# ==================================================

def _load_state():
    if not os.path.exists(STATE_FILE):
        return {"active": False, "day": 0, "start_date": None, "stage": None}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def _today_utc_date_str():
    return datetime.utcnow().date().isoformat()

def _is_support(chat_id: int) -> bool:
    return chat_id == SUPPORT_GROUP_ID


# ==================================================
# FORMAT LB
# ==================================================

def _format_lb(users, limit=15):
    if not users:
        return "No participants yet."

    lines = []
    medals = ["🥇", "🥈", "🥉"]

    for i, u in enumerate(users[:limit]):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = html.escape(u.get("username", "User"))
        pts = u.get("tournament_points", 0)
        lines.append(f"{medal} {name} — <b>{pts}</b>")

    return "\n".join(lines)


# ==================================================
# AUTO ADVANCE
# ==================================================

async def _advance_if_needed(state, context: ContextTypes.DEFAULT_TYPE):
    if not state.get("active"):
        return state

    start_date_str = state.get("start_date")
    if not start_date_str:
        return state

    start_date = date.fromisoformat(start_date_str)
    today = datetime.utcnow().date()
    elapsed_days = (today - start_date).days

    new_day = min(4, elapsed_days + 1)

    if new_day == state["day"]:
        return state

    state = await _run_stage_transition(state, new_day, context)
    return state


async def _run_stage_transition(state, new_day: int, context: ContextTypes.DEFAULT_TYPE):
    from database import _users

    state["day"] = new_day
    stage, qualify_n = STAGES[new_day]
    state["stage"] = stage
    _save_state(state)

    _users.update_many(
        {"tournament_joined": True},
        {"$set": {"tournament_qualified": False}}
    )

    if new_day == 1:
        _users.update_many(
            {"tournament_joined": True},
            {"$set": {"tournament_qualified": True}}
        )
    else:
        lb = get_tournament_leaderboard(limit=1000)
        qualified_ids = [u["_id"] for u in lb[:qualify_n]] if qualify_n else []

        if qualified_ids:
            _users.update_many(
                {"_id": {"$in": qualified_ids}},
                {"$set": {"tournament_qualified": True}}
            )

    reset_tournament_points_only()

    # ✅ Proper async announcement
    if SUPPORT_GROUP_ID:
        msg = (
            f"🏁 <b>Stage Updated!</b>\n"
            f"Day <b>{new_day}</b>: <b>{stage.title()}</b>\n"
        )

        if qualify_n:
            msg += f"✅ Qualified: Top <b>{qualify_n}</b>\n"

        msg += "\nUse /tleaderboard to see standings."

        try:
            await context.bot.send_message(
                chat_id=SUPPORT_GROUP_ID,
                text=msg,
                parse_mode="HTML"
            )
        except Exception:
            pass

    return state


# ==================================================
# COMMANDS
# ==================================================

async def tstart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Only admin can start tournament.")
        return

    if not _is_support(update.effective_chat.id):
        await update.message.reply_text("Tournament only runs in support group.")
        return

    reset_tournament_all()

    state = {
        "active": True,
        "day": 1,
        "start_date": _today_utc_date_str(),
        "stage": "normal",
    }

    _save_state(state)

    await update.message.reply_text(
        "🏆 <b>4-Day Tournament Started!</b>\n\n"
        "Day 1: Normal\n"
        "Day 2: Quarter (Top 16)\n"
        "Day 3: Semi (Top 8)\n"
        "Day 4: Final (Top 4)\n\n"
        "✅ Join: /tjoin\n"
        "📊 Leaderboard: /tleaderboard\n"
        "ℹ Status: /tstatus\n\n"
        "🎁 Prize: Winner gets <b>DOUBLE POINTS for 3 days</b>",
        parse_mode="HTML"
    )


async def tjoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    state = _load_state()
    state = await _advance_if_needed(state, context)
    _save_state(state)

    if not state.get("active"):
        await update.message.reply_text("No active tournament.")
        return

    if not _is_support(update.effective_chat.id):
        await update.message.reply_text("Tournament only runs in support group.")
        return

    user = update.effective_user
    join_tournament(user.id, user.first_name)

    await update.message.reply_text(
        f"✅ Joined!\nCurrent Stage: <b>{state['stage'].title()}</b> (Day {state['day']}/4)",
        parse_mode="HTML"
    )


async def tleaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    state = _load_state()
    state = await _advance_if_needed(state, context)
    _save_state(state)

    if not state.get("active"):
        await update.message.reply_text("No active tournament.")
        return

    users = get_tournament_leaderboard(limit=15)

    text = (
        f"🏆 <b>TOURNAMENT LEADERBOARD</b>\n"
        f"<code>Day {state['day']}/4 • {state['stage'].title()}</code>\n\n"
        f"{_format_lb(users)}"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def tstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    state = _load_state()
    state = await _advance_if_needed(state, context)
    _save_state(state)

    if not state.get("active"):
        await update.message.reply_text("No active tournament.")
        return

    await update.message.reply_text(
        f"ℹ <b>Tournament Status</b>\n\n"
        f"Active: <b>Yes</b>\n"
        f"Start Date (UTC): <b>{state['start_date']}</b>\n"
        f"Day: <b>{state['day']}/4</b>\n"
        f"Stage: <b>{state['stage'].title()}</b>",
        parse_mode="HTML"
    )


async def tend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Only admin can end tournament.")
        return

    state = _load_state()

    if not state.get("active"):
        await update.message.reply_text("No active tournament.")
        return

    lb = get_tournament_leaderboard(limit=3)

    text = "🏁 <b>Tournament Finished!</b>\n\n"

    if lb:
        text += _format_lb(lb, limit=3) + "\n\n"
        winner_id = lb[0]["_id"]
        set_double_points_prize(winner_id, days=3)
        text += "🎁 Prize: Winner got <b>DOUBLE POINTS for 3 days</b>"
    else:
        text += "No winners."

    reset_tournament_all()
    _save_state({"active": False, "day": 0, "start_date": None, "stage": None})

    await update.message.reply_text(text, parse_mode="HTML")