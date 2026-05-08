import os
import html
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

load_dotenv()

LOGGER_GROUP_ID = int(os.getenv("LOGGER_GROUP_ID", "0"))

# ==================================================
# BOT ADDED TO GROUP LOGGER
# ==================================================

async def bot_added_logger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.my_chat_member:
        return

    chat = update.effective_chat
    new_status = update.my_chat_member.new_chat_member.status
    old_status = update.my_chat_member.old_chat_member.status

    # Detect when bot is added
    if old_status in ("left", "kicked") and new_status in ("member", "administrator"):

        if chat.type not in ["group", "supergroup"]:
            return

        # Who added the bot
        added_by = update.effective_user
        adder_name = html.escape(added_by.full_name)
        adder_id = added_by.id

        # Group details
        group_name = html.escape(chat.title)
        chat_id = chat.id

        try:
            member_count = await context.bot.get_chat_member_count(chat_id)
        except:
            member_count = "Unknown"

        # Public link
        invite_link = ""
        if chat.username:
            invite_link = f"https://t.me/{chat.username}"
        else:
            invite_link = "Private Group"

        text = (
            f"🤖 <b>Bot Added to Group</b>\n\n"
            f"📌 Group: <b>{group_name}</b>\n"
            f"🆔 Chat ID: <code>{chat_id}</code>\n"
            f"👥 Members: <b>{member_count}</b>\n"
            f"🔗 Link: {invite_link}\n\n"
            f"➕ Added By: <b>{adder_name}</b>"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "👤 Added By ID",
                    callback_data=f"adder_{adder_id}"
                )
            ]
        ])

        await context.bot.send_message(
            chat_id=LOGGER_GROUP_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )


# ==================================================
# DM START LOGGER
# ==================================================

async def dm_start_logger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    name = html.escape(user.full_name)
    user_id = user.id
    username = f"@{user.username}" if user.username else "No username"

    text = (
        f"📩 <b>User Started Bot (DM)</b>\n\n"
        f"👤 Name: <b>{name}</b>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🔗 Username: {username}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔎 Open Profile",
                url=f"tg://user?id={user_id}"
            )
        ]
    ])

    await context.bot.send_message(
        chat_id=LOGGER_GROUP_ID,
        text=text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ==================================================
# CALLBACK FOR ADDER BUTTON
# ==================================================

async def logger_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("adder_"):
        user_id = query.data.split("_")[1]
        await query.answer(f"Added by User ID: {user_id}", show_alert=True)