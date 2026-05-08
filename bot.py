import os
from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters
)

# ==================================================
# LOAD ENV
# ==================================================

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")

# ==================================================
# IMPORT COMMANDS
# ==================================================

# 🎮 Game
from commands.start import start, start_callback
from commands.new import new, new4, new5, new6, new7
from commands.end import end, end4, end5, end6, end7
from commands.guess import guess
from commands.leaderboard import leaderboard, leaderboard_callback
from commands.rank import rank
from commands.add import add_word
from commands.remove import remove_word

# 🏆 Tournament
from commands.tournament import (
    tstart,
    tjoin,
    tleaderboard,
    tstatus,
    tend
)

# 👑 Owner
from commands.owner import (
    transfer,
    transferbypts,
    resetpoints,
    searchpoints,
    viewuser,
    deleteuser
)

# 📊 Logger
from commands.logger import (
    bot_added_logger,
    dm_start_logger,
    logger_callback
)

# 🔎 Topic ID command
from commands.topicid import topicid

from database import ensure_indexes


# ==================================================
# MAIN
# ==================================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Ensure MongoDB indexes
    ensure_indexes()

    # ==================================================
    # 🤖 LOGGER SYSTEM
    # ==================================================

    app.add_handler(
        ChatMemberHandler(
            bot_added_logger,
            ChatMemberHandler.MY_CHAT_MEMBER
        )
    )

    # DM start logger (runs before normal start)
    app.add_handler(CommandHandler("start", dm_start_logger), group=0)

    # ==================================================
    # 🎮 GAME COMMANDS
    # ==================================================

    app.add_handler(CommandHandler("start", start), group=1)

    # Topic ID checker
    app.add_handler(CommandHandler("topicid", topicid))

    # New game commands
    app.add_handler(CommandHandler("new", new))
    app.add_handler(CommandHandler("new4", new4))
    app.add_handler(CommandHandler("new5", new5))
    app.add_handler(CommandHandler("new6", new6))
    app.add_handler(CommandHandler("new7", new7))

    # End game commands
    app.add_handler(CommandHandler("end", end))
    app.add_handler(CommandHandler("end4", end4))
    app.add_handler(CommandHandler("end5", end5))
    app.add_handler(CommandHandler("end6", end6))
    app.add_handler(CommandHandler("end7", end7))

    # Stats
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("rank", rank))

    # Word management
    app.add_handler(CommandHandler("add", add_word))
    app.add_handler(CommandHandler("remove", remove_word))

    # ==================================================
    # 🏆 TOURNAMENT COMMANDS
    # ==================================================

    app.add_handler(CommandHandler("tstart", tstart))
    app.add_handler(CommandHandler("tjoin", tjoin))
    app.add_handler(CommandHandler("tleaderboard", tleaderboard))
    app.add_handler(CommandHandler("tstatus", tstatus))
    app.add_handler(CommandHandler("tend", tend))

    # ==================================================
    # 👑 OWNER COMMANDS
    # ==================================================

    app.add_handler(CommandHandler("transfer", transfer))
    app.add_handler(CommandHandler("transferbypts", transferbypts))
    app.add_handler(CommandHandler("resetpoints", resetpoints))
    app.add_handler(CommandHandler("searchpoints", searchpoints))
    app.add_handler(CommandHandler("viewuser", viewuser))
    app.add_handler(CommandHandler("deleteuser", deleteuser))

    # ==================================================
    # 🔘 CALLBACK HANDLERS
    # ==================================================

    app.add_handler(CallbackQueryHandler(start_callback, pattern="help_panel"))
    app.add_handler(CallbackQueryHandler(leaderboard_callback, pattern="^lb_"))
    app.add_handler(CallbackQueryHandler(logger_callback, pattern="^(adder_|uid_)"))

    # ==================================================
    # ✍ TEXT HANDLER (GUESS)
    # ==================================================

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, guess)
    )

    print("WordSix Bot Running (Game + Tournament + Owner + Logger)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()