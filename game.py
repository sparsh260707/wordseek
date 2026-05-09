import os
import random
import json
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple

from api import get_meaning

MAX_GUESSES = 30

# ---------------- PATH SETUP ----------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORDS_DIR = os.path.join(BASE_DIR, "words")

# ---------------- WORD CACHE ----------------

WORD_CACHE: Dict[int, Dict[str, List[str]]] = {}

# Support for all word lengths
FILE_MAP = {
    4: ("common-four.json", "all-four.json"),
    5: ("common-five.json", "all-five.json"),
    6: ("common-six.json", "all-six.json"),
    7: ("common-seven.json", "all-seven.json"),
}


def _extract_words(data):
    """Extract words from JSON data (supports both list and dict formats)"""
    if isinstance(data, dict) and "words" in data:
        return data["words"]
    return data


def load_word_files(word_len: int):
    """Load answers and allowed words for given word length"""
    
    if word_len in WORD_CACHE:
        return WORD_CACHE[word_len]

    if word_len not in FILE_MAP:
        raise ValueError(f"Unsupported word length: {word_len}. Supported lengths: 4, 5, 6, 7")

    answers_file = os.path.join(WORDS_DIR, FILE_MAP[word_len][0])
    allowed_file = os.path.join(WORDS_DIR, FILE_MAP[word_len][1])

    if not os.path.exists(answers_file):
        raise FileNotFoundError(f"Missing file: {answers_file}")

    if not os.path.exists(allowed_file):
        raise FileNotFoundError(f"Missing file: {allowed_file}")

    with open(answers_file, "r", encoding="utf-8") as f:
        answers_raw = json.load(f)

    with open(allowed_file, "r", encoding="utf-8") as f:
        allowed_raw = json.load(f)

    answers_raw = _extract_words(answers_raw)
    allowed_raw = _extract_words(allowed_raw)

    answers = [w.lower() for w in answers_raw if w.isalpha() and len(w) == word_len]
    allowed = [w.lower() for w in allowed_raw if w.isalpha() and len(w) == word_len]

    if not answers:
        raise ValueError(f"Answer list empty for {word_len}-letter words")

    # Allowed guesses = all words from both files
    WORD_CACHE[word_len] = {
        "answers": answers,
        "allowed": list(set(allowed + answers))
    }

    return WORD_CACHE[word_len]


def get_all_supported_lengths() -> List[int]:
    """Return list of all supported word lengths"""
    return list(FILE_MAP.keys())


# ---------------- MEANINGS ----------------

MEANINGS: Dict[str, dict] = {}
MEANING_FILE = os.path.join(WORDS_DIR, "commonWords.json")

if os.path.exists(MEANING_FILE):
    try:
        with open(MEANING_FILE, "r", encoding="utf-8") as f:
            MEANINGS = json.load(f)
    except:
        MEANINGS = {}


def get_word_meaning(word: str) -> str:
    """Get meaning of a word from local cache or API"""
    word = word.lower()

    if word in MEANINGS:
        data = MEANINGS[word]

        if isinstance(data, dict):
            meaning = data.get("meaning", "")
            pronunciation = data.get("pronunciation", "")
            example = data.get("example", "")

            parts = []

            if pronunciation:
                parts.append(f"🔊 {pronunciation}")

            if meaning:
                parts.append(f"📖 {meaning}")

            if example:
                parts.append(f"📝 Example:\n{example}")

            return "\n\n".join(parts)

        return str(data)

    try:
        meaning = get_meaning(word)
        if meaning:
            return str(meaning)
    except:
        pass

    return "Meaning not available."


# ---------------- GAME STATE ----------------

@dataclass
class GameState:
    chat_id: int
    thread_id: int
    answer: str
    word_len: int
    guesses: List[str] = field(default_factory=list)
    board: List[str] = field(default_factory=list)
    active: bool = True


GAMES: Dict[Tuple[int, int], GameState] = {}


# ---------------- GAME MANAGEMENT ----------------

def new_game(chat_id: int, thread_id: int, word_len: int) -> GameState:
    """Create a new game with specified word length"""
    word_data = load_word_files(word_len)
    answer = random.choice(word_data["answers"])

    state = GameState(
        chat_id=chat_id,
        thread_id=thread_id,
        answer=answer,
        word_len=word_len
    )

    GAMES[(chat_id, thread_id)] = state
    return state


def get_game(chat_id: int, thread_id: int) -> Optional[GameState]:
    """Get existing game for given chat/thread"""
    return GAMES.get((chat_id, thread_id))


def end_game(chat_id: int, thread_id: int) -> None:
    """Mark game as inactive"""
    key = (chat_id, thread_id)
    if key in GAMES:
        GAMES[key].active = False


def remove_game(chat_id: int, thread_id: int) -> None:
    """Remove game from memory"""
    GAMES.pop((chat_id, thread_id), None)


def game_exists(chat_id: int, thread_id: int) -> bool:
    """Check if an active game exists"""
    game = get_game(chat_id, thread_id)
    return game is not None and game.active


# ---------------- SCORING ----------------

def score_guess(guess: str, answer: str) -> str:
    """
    Score a guess against the answer
    🟩 = correct letter, correct position
    🟨 = correct letter, wrong position
    🟥 = wrong letter
    """
    word_len = len(answer)

    result = ["🟥"] * word_len
    answer_chars = list(answer)

    # First pass: mark correct positions
    for i in range(word_len):
        if guess[i] == answer[i]:
            result[i] = "🟩"
            answer_chars[i] = None

    # Second pass: mark correct letters in wrong positions
    for i in range(word_len):
        if result[i] == "🟩":
            continue
        if guess[i] in answer_chars:
            result[i] = "🟨"
            # Remove the used character
            answer_chars[answer_chars.index(guess[i])] = None

    return "".join(result)


# ---------------- BOARD ----------------

def add_guess(state: GameState, guess: str) -> Optional[str]:
    """
    Add a guess to the game state
    Returns formatted line for board or error message
    """
    guess = guess.lower()

    # Check length
    if len(guess) != state.word_len:
        return f"Word must be {state.word_len} letters"

    # Check if word is allowed
    word_data = load_word_files(state.word_len)
    allowed_set: Set[str] = set(word_data["allowed"])

    if guess not in allowed_set:
        return f"'{guess.upper()}' is not a valid word"

    # Check for duplicate guess
    if guess in state.guesses:
        return None  # Silent ignore for duplicates

    # Score the guess
    colors = score_guess(guess, state.answer)
    spaced = " ".join(list(colors))

    # Format board line
    line = f"{spaced}  <b>{guess.upper()}</b>"

    state.guesses.append(guess)
    state.board.append(line)

    return line


def build_board(state: GameState) -> str:
    """Build the complete game board as string"""
    if not state.board:
        return "No guesses yet!"
    return "\n".join(state.board)


def get_remaining_guesses(state: GameState) -> int:
    """Get number of guesses remaining"""
    return MAX_GUESSES - len(state.guesses)


def is_win(state: GameState) -> bool:
    """Check if game is won"""
    return state.answer in state.guesses


def is_game_over(state: GameState) -> bool:
    """Check if game is over (win/loss/inactive)"""
    return (
        not state.active
        or is_win(state)
        or len(state.guesses) >= MAX_GUESSES
    )


def reveal_answer_text(state: GameState) -> str:
    """Get formatted answer reveal text with meaning"""
    meaning = get_word_meaning(state.answer)

    return (
        f"\n\n🎯 Answer: <b>{state.answer.upper()}</b>\n\n"
        f"{meaning}"
    )


def get_game_stats(state: GameState) -> Dict:
    """Get statistics for current game"""
    return {
        "word_length": state.word_len,
        "guesses_used": len(state.guesses),
        "guesses_remaining": MAX_GUESSES - len(state.guesses),
        "is_won": is_win(state),
        "is_over": is_game_over(state),
        "answer": state.answer if is_game_over(state) else None
    }


# ---------------- HELPER FUNCTIONS ----------------

def validate_word_length(word_len: int) -> bool:
    """Check if word length is supported"""
    return word_len in FILE_MAP


def get_random_word(word_len: int) -> Optional[str]:
    """Get a random answer word for testing"""
    try:
        word_data = load_word_files(word_len)
        return random.choice(word_data["answers"])
    except:
        return None


def get_word_count(word_len: int) -> Dict[str, int]:
    """Get word counts for given length"""
    try:
        word_data = load_word_files(word_len)
        return {
            "answers": len(word_data["answers"]),
            "allowed": len(word_data["allowed"])
        }
    except:
        return {"answers": 0, "allowed": 0}