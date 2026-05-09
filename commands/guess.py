from telegram import Update
from telegram.ext import ContextTypes
import html
import random
import asyncio

from game import (
    get_game,
    add_guess,
    build_board,
    MAX_GUESSES
)

from database import (
    register_user,
    add_points,
    update_stats,
    add_tournament_points,
    get_user
)


async def send_fast_reaction(bot, chat_id, message_id):
    try:
        reactions = ["🔥", "🎉", "🏆", "💎", "⚡", "👑", "🌟", "🚀", "🎯", "🥳"]
        await bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=random.choice(reactions)
        )
    except:
        pass


async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.message
    if not message:
        return

    chat_id = update.effective_chat.id
    thread_id = message.message_thread_id
    user = update.effective_user

    state = get_game(chat_id, thread_id)

    if not state or not state.active:
        return

    if message.text:
        guess_word = message.text.strip().lower()
    else:
        return

    if len(guess_word) != state.word_len or not guess_word.isalpha():
        return

    # Check if word is valid (in allowed list)
    from game import load_word_files
    word_data = load_word_files(state.word_len)
    if guess_word not in word_data["allowed"]:
        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=f"❌ {guess_word.upper()} is not a valid {state.word_len}-letter word.",
            reply_to_message_id=message.message_id
        )
        return

    # Check if correct word
    if guess_word == state.answer:
        state.active = False

        register_user(user.id, user.first_name)

        # POINTS FORMULA: 30 - guesses_used
        guesses_used = len(state.guesses) + 1  # +1 for current correct guess
        points = 30 - guesses_used
        
        # Ensure points don't go negative
        if points < 0:
            points = 0

        add_points(user.id, chat_id, points)

        user_data = get_user(user.id)
        if user_data and user_data.get("tournament_joined"):
            add_tournament_points(user.id, points)

        update_stats(
            user_id=user.id,
            username=user.first_name,
            win=True,
            attempts_used=guesses_used
        )

        # Win message with BLACKQUOTE
        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=(
                f"<blockquote>\n"
                f"Congrats! You guessed it correctly.\n"
                f"Correct Word: {state.answer}\n"
                f"Added {points} to the leaderboard.\n"
                f"Start with /new{state.word_len}"
                f"</blockquote>\n\n"
            ),
            parse_mode="HTML",
            reply_to_message_id=message.message_id
        )

        asyncio.create_task(
            send_fast_reaction(context.bot, chat_id, message.message_id)
        )

        return

    # For wrong guesses - process normally
    result = add_guess(state, guess_word)

    if result is None:
        return

    # Send board update for wrong guesses only
    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=build_board(state),
        parse_mode="HTML"
    )

    # Loss condition
    if len(state.guesses) >= MAX_GUESSES:
        state.active = False

        register_user(user.id, user.first_name)

        update_stats(
            user_id=user.id,
            username=user.first_name,
            win=False,
            attempts_used=MAX_GUESSES
        )

        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=(
                f"❌ Game Over!\n\n"
                f"<blockquote>\n"
                f"Correct Word: {state.answer}\n"
                f"</blockquote>\n\n"
                f"Start with /new{state.word_len}"
            ),
            parse_mode="HTML"
        )