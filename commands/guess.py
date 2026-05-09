from telegram import Update
from telegram.ext import ContextTypes
import html
import random
import asyncio

from game import (
    get_game,
    add_guess,
    build_board,
    MAX_GUESSES,
    load_word_files,
    is_game_over,
    reveal_answer_text
)

from database import (
    register_user,
    add_points,
    update_stats,
    add_tournament_points,
    get_user,
    add_word_score  # Added for word storage
)


async def send_fast_reaction(bot, chat_id, message_id):
    """Send a random reaction to a message"""
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
    """Handle guess messages"""
    
    message = update.message
    if not message:
        return

    chat_id = update.effective_chat.id
    thread_id = message.message_thread_id or 0
    user = update.effective_user

    # Get existing game state
    state = get_game(chat_id, thread_id)

    if not state or not state.active:
        return

    # Get the guess word
    if message.text:
        guess_word = message.text.strip().lower()
    else:
        return

    # Validate word length and characters
    if len(guess_word) != state.word_len or not guess_word.isalpha():
        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=f"⚠️ Word must be {state.word_len} letters and contain only alphabets.",
            reply_to_message_id=message.message_id
        )
        return

    # Check if word is valid (in allowed list)
    word_data = load_word_files(state.word_len)
    if guess_word not in word_data["allowed"]:
        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=f"❌ <b>{guess_word.upper()}</b> is not a valid {state.word_len}-letter word.",
            parse_mode="HTML",
            reply_to_message_id=message.message_id
        )
        return

    # Check for duplicate guess
    if guess_word in state.guesses:
        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=f"ℹ️ You already guessed <b>{guess_word.upper()}</b>",
            parse_mode="HTML",
            reply_to_message_id=message.message_id
        )
        return

    # --- CORRECT GUESS ---
    if guess_word == state.answer:
        state.active = False

        # Register user if not exists
        register_user(user.id, user.first_name)

        # Calculate points: base points + bonus for fewer guesses
        guesses_used = len(state.guesses) + 1  # +1 for current correct guess
        base_points = 30 - guesses_used
        word_bonus = len(state.answer) * 2  # Bonus based on word length
        
        points = base_points + word_bonus
        
        # Ensure points don't go negative
        if points < 0:
            points = 0

        # Add points to leaderboard and store word
        add_points(user.id, chat_id, points, word=state.answer)
        
        # Store the word in user's history
        add_word_score(user.id, state.answer, points, chat_id)

        # Tournament points if applicable
        user_data = get_user(user.id)
        if user_data and user_data.get("tournament_joined"):
            add_tournament_points(user.id, points)

        # Update game statistics
        update_stats(
            user_id=user.id,
            username=user.first_name,
            win=True,
            attempts_used=guesses_used,
            word_length=state.word_len
        )

        # Get word meaning for the win message
        from game import get_word_meaning
        meaning = get_word_meaning(state.answer)
        
        # Win message with details
        win_text = (
            f"🎉 <b>CORRECT!</b> 🎉\n\n"
            f"<blockquote>\n"
            f"Word: <b>{state.answer.upper()}</b>\n"
            f"Guesses: {guesses_used}/{MAX_GUESSES}\n"
            f"Points earned: <b>+{points}</b>\n"
        )
        
        if meaning and meaning != "Meaning not available.":
            win_text += f"\n📖 {meaning}\n"
        
        win_text += f"</blockquote>\n\n"
        win_text += f"➡️ Start a new game: /new{state.word_len}"
        
        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=win_text,
            parse_mode="HTML",
            reply_to_message_id=message.message_id
        )

        # Send reaction
        asyncio.create_task(
            send_fast_reaction(context.bot, chat_id, message.message_id)
        )

        return

    # --- WRONG GUESS ---
    # Add the guess to game state
    result = add_guess(state, guess_word)

    if result is None:
        # This shouldn't happen as we already checked duplicates
        return

    # Send updated board
    board_text = build_board(state)
    remaining = MAX_GUESSES - len(state.guesses)
    
    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=f"{board_text}\n\n📊 Remaining guesses: {remaining}",
        parse_mode="HTML"
    )

    # --- LOSS CONDITION ---
    if len(state.guesses) >= MAX_GUESSES:
        state.active = False

        # Register user if not exists
        register_user(user.id, user.first_name)

        # Update statistics for loss
        update_stats(
            user_id=user.id,
            username=user.first_name,
            win=False,
            attempts_used=MAX_GUESSES,
            word_length=state.word_len
        )

        # Get word meaning
        from game import get_word_meaning
        meaning = get_word_meaning(state.answer)

        # Loss message
        loss_text = (
            f"❌ <b>GAME OVER!</b> ❌\n\n"
            f"<blockquote>\n"
            f"Correct Word: <b>{state.answer.upper()}</b>\n"
        )
        
        if meaning and meaning != "Meaning not available.":
            loss_text += f"\n📖 {meaning}\n"
        
        loss_text += f"</blockquote>\n\n"
        loss_text += f"➡️ Try again: /new{state.word_len}"

        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=loss_text,
            parse_mode="HTML"
        )
