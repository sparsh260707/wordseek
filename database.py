import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient, DESCENDING

# ==================================================
# ENV
# ==================================================

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "").strip()

if not MONGO_URI:
    raise ValueError("MONGO_URI missing in .env")

_client = MongoClient(MONGO_URI)
_db = _client["wordseek"]
_users = _db["users"]

# ==================================================
# INDEXES
# ==================================================

def ensure_indexes():
    _users.create_index([("global_points", DESCENDING)])
    _users.create_index([("daily_points", DESCENDING)])
    _users.create_index([("weekly_points", DESCENDING)])
    _users.create_index([("monthly_points", DESCENDING)])
    _users.create_index([("yearly_points", DESCENDING)])
    _users.create_index([("wins", DESCENDING)])
    _users.create_index([("tournament_points", DESCENDING)])
    _users.create_index([("chat_points", DESCENDING)])

# ==================================================
# REGISTER USER
# ==================================================

def register_user(user_id: int, username: str):
    now = datetime.utcnow()

    _users.update_one(
        {"_id": user_id},
        {
            "$setOnInsert": {
                "username": username,
                "games": 0,
                "wins": 0,
                "streak": 0,
                "best": 999999,

                "global_points": 0,
                "daily_points": 0,
                "weekly_points": 0,
                "monthly_points": 0,
                "yearly_points": 0,

                "chat_points": {},

                "tournament_points": 0,
                "tournament_joined": False,
                "tournament_qualified": False,

                "double_points_until": None,

                "last_daily_reset": now,
                "last_week_reset": now.isocalendar()[1],
                "last_month_reset": now.month,
                "last_year_reset": now.year,
            }
        },
        upsert=True
    )

# ==================================================
# RESET CHECK
# ==================================================

def _check_and_reset(user):
    now = datetime.utcnow()
    updates = {}

    if not user.get("last_daily_reset") or user["last_daily_reset"].date() != now.date():
        updates["daily_points"] = 0
        updates["last_daily_reset"] = now

    if user.get("last_week_reset") != now.isocalendar()[1]:
        updates["weekly_points"] = 0
        updates["last_week_reset"] = now.isocalendar()[1]

    if user.get("last_month_reset") != now.month:
        updates["monthly_points"] = 0
        updates["last_month_reset"] = now.month

    if user.get("last_year_reset") != now.year:
        updates["yearly_points"] = 0
        updates["last_year_reset"] = now.year

    if updates:
        _users.update_one({"_id": user["_id"]}, {"$set": updates})

# ==================================================
# ADD POINTS
# ==================================================

def add_points(user_id: int, chat_id: int, points: int):
    user = _users.find_one({"_id": user_id})

    if not user:
        register_user(user_id, "User")
        user = _users.find_one({"_id": user_id})

    _check_and_reset(user)

    now = datetime.utcnow()
    double_until = user.get("double_points_until")

    if double_until and now < double_until:
        points *= 2

    _users.update_one(
        {"_id": user_id},
        {
            "$inc": {
                "global_points": points,
                "daily_points": points,
                "weekly_points": points,
                "monthly_points": points,
                "yearly_points": points,
                f"chat_points.{chat_id}": points
            }
        }
    )

# ==================================================
# GAME STATS
# ==================================================

def update_stats(user_id: int, username: str, win: bool, attempts_used: int):
    user = _users.find_one({"_id": user_id})

    if not user:
        register_user(user_id, username)
        user = _users.find_one({"_id": user_id})

    games = user.get("games", 0) + 1
    wins = user.get("wins", 0)
    streak = user.get("streak", 0)
    best = user.get("best", 999999)

    if win:
        wins += 1
        streak += 1
        best = min(best, attempts_used)
    else:
        streak = 0

    _users.update_one(
        {"_id": user_id},
        {
            "$set": {
                "username": username,
                "games": games,
                "wins": wins,
                "streak": streak,
                "best": best
            }
        }
    )

# ==================================================
# TOURNAMENT FUNCTIONS
# ==================================================

def join_tournament(user_id: int, username: str):
    register_user(user_id, username)
    _users.update_one(
        {"_id": user_id},
        {"$set": {
            "username": username,
            "tournament_joined": True,
            "tournament_qualified": True
        }}
    )

def add_tournament_points(user_id: int, points: int):
    _users.update_one(
        {
            "_id": user_id,
            "tournament_joined": True,
            "tournament_qualified": True
        },
        {"$inc": {"tournament_points": points}}
    )

def reset_tournament_all():
    _users.update_many(
        {},
        {"$set": {
            "tournament_points": 0,
            "tournament_joined": False,
            "tournament_qualified": False
        }}
    )

def reset_tournament_points_only():
    _users.update_many(
        {"tournament_joined": True},
        {"$set": {"tournament_points": 0}}
    )

def get_tournament_leaderboard(limit=16):
    return list(
        _users.find({
            "tournament_joined": True,
            "username": {"$exists": True, "$ne": ""}
        })
        .sort("tournament_points", DESCENDING)
        .limit(limit)
    )

# ==================================================
# DOUBLE POINT PRIZE
# ==================================================

def set_double_points_prize(user_id: int, days: int = 3):
    until = datetime.utcnow() + timedelta(days=days)
    _users.update_one(
        {"_id": user_id},
        {"$set": {"double_points_until": until}}
    )
    return until

# ==================================================
# LEADERBOARDS
# ==================================================

def get_global_leaderboard(period="all", limit=16):
    field_map = {
        "today": "daily_points",
        "week": "weekly_points",
        "month": "monthly_points",
        "year": "yearly_points",
        "all": "global_points"
    }

    field = field_map.get(period, "global_points")

    return list(
        _users.find({
            field: {"$gt": 0},
            "username": {"$exists": True, "$ne": ""}
        })
        .sort(field, DESCENDING)
        .limit(limit)
    )

def get_chat_leaderboard(chat_id: int, period="all", limit=16):

    if period == "all":
        return list(
            _users.find({
                f"chat_points.{chat_id}": {"$gt": 0},
                "username": {"$exists": True, "$ne": ""}
            })
            .sort(f"chat_points.{chat_id}", DESCENDING)
            .limit(limit)
        )

    period_map = {
        "today": "daily_points",
        "week": "weekly_points",
        "month": "monthly_points",
        "year": "yearly_points",
    }

    field = period_map.get(period, "daily_points")

    return list(
        _users.find({
            f"chat_points.{chat_id}": {"$exists": True},
            field: {"$gt": 0},
            "username": {"$exists": True, "$ne": ""}
        })
        .sort(field, DESCENDING)
        .limit(limit)
    )

# ==================================================
# USER FETCH
# ==================================================

def get_user(user_id: int):
    return _users.find_one({"_id": user_id})

def get_user_profile(user_id: int):
    return _users.find_one({"_id": user_id})