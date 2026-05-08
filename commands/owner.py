import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes
from pymongo import MongoClient

load_dotenv()

ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
MONGO_URI = os.getenv("MONGO_URI")

_client = MongoClient(MONGO_URI)
_db = _client["wordseek"]
_users = _db["users"]


# ==================================================
# HELPER
# ==================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ==================================================
# TRANSFER BY USER ID
# /transfer old_id new_id
# ==================================================

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage:\n/transfer old_id new_id")
        return

    old_id = int(context.args[0])
    new_id = int(context.args[1])

    old_user = _users.find_one({"_id": old_id})
    new_user = _users.find_one({"_id": new_id})

    if not old_user:
        await update.message.reply_text("Old user not found.")
        return

    if not new_user:
        await update.message.reply_text("New user not found.")
        return

    numeric_fields = [
        "global_points",
        "daily_points",
        "weekly_points",
        "monthly_points",
        "yearly_points",
        "tournament_points",
        "games",
        "wins",
        "streak"
    ]

    update_data = {}

    for field in numeric_fields:
        update_data[field] = new_user.get(field, 0) + old_user.get(field, 0)

    # Merge chat points
    old_chat = old_user.get("chat_points", {})
    new_chat = new_user.get("chat_points", {})

    for chat_id, pts in old_chat.items():
        new_chat[chat_id] = new_chat.get(chat_id, 0) + pts

    update_data["chat_points"] = new_chat

    _users.update_one({"_id": new_id}, {"$set": update_data})

    await update.message.reply_text("✅ Transfer successful.")


# ==================================================
# TRANSFER BY POINTS
# /transferbypts points new_id
# ==================================================

async def transferbypts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage:\n/transferbypts points new_id")
        return

    points = int(context.args[0])
    new_id = int(context.args[1])

    old_user = _users.find_one({"global_points": points})
    new_user = _users.find_one({"_id": new_id})

    if not old_user:
        await update.message.reply_text("No user found with those points.")
        return

    if not new_user:
        await update.message.reply_text("New user not found.")
        return

    context.args = [str(old_user["_id"]), str(new_id)]
    await transfer(update, context)


# ==================================================
# RESET USER
# /resetpoints user_id
# ==================================================

async def resetpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage:\n/resetpoints user_id")
        return

    user_id = int(context.args[0])

    _users.update_one(
        {"_id": user_id},
        {
            "$set": {
                "global_points": 0,
                "daily_points": 0,
                "weekly_points": 0,
                "monthly_points": 0,
                "yearly_points": 0,
                "tournament_points": 0,
                "chat_points": {},
                "games": 0,
                "wins": 0,
                "streak": 0
            }
        }
    )

    await update.message.reply_text("✅ User points reset.")


# ==================================================
# SEARCH USERS BY MIN POINTS
# /searchpoints min_points
# ==================================================

async def searchpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage:\n/searchpoints min_points")
        return

    min_pts = int(context.args[0])

    users = list(_users.find({"global_points": {"$gte": min_pts}}).limit(20))

    if not users:
        await update.message.reply_text("No users found.")
        return

    text = "Users Found:\n\n"

    for u in users:
        text += f"ID: {u['_id']} | Points: {u.get('global_points',0)}\n"

    await update.message.reply_text(text)


# ==================================================
# VIEW USER
# /viewuser user_id
# ==================================================

async def viewuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage:\n/viewuser user_id")
        return

    user_id = int(context.args[0])
    user = _users.find_one({"_id": user_id})

    if not user:
        await update.message.reply_text("User not found.")
        return

    text = (
        f"👤 User ID: {user_id}\n"
        f"Points: {user.get('global_points',0)}\n"
        f"Wins: {user.get('wins',0)}\n"
        f"Games: {user.get('games',0)}\n"
    )

    await update.message.reply_text(text)


# ==================================================
# DELETE USER
# /deleteuser user_id
# ==================================================

async def deleteuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage:\n/deleteuser user_id")
        return

    user_id = int(context.args[0])
    _users.delete_one({"_id": user_id})

    await update.message.reply_text("✅ User deleted from database.")