import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MW_API_KEY", "").strip()
BASE_URL = "https://dictionaryapi.com/api/v3/references/collegiate/json/"

# RAM cache (resets on restart)
_MEANING_CACHE = {}


def get_meaning(word: str) -> str:
    word = word.lower().strip()

    if word in _MEANING_CACHE:
        return _MEANING_CACHE[word]

    if not API_KEY:
        return "Dictionary API key missing."

    try:
        url = f"{BASE_URL}{word}?key={API_KEY}"
        response = requests.get(url, timeout=8)

        if response.status_code != 200:
            return "Meaning not found."

        data = response.json()

        # If suggestions list returned instead of dictionary entry
        if not data or isinstance(data[0], str):
            return "Meaning not found."

        entry = data[0]

        part_of_speech = entry.get("fl", "")
        shortdefs = entry.get("shortdef", [])

        if shortdefs:
            definition = shortdefs[0]
            meaning = f"{part_of_speech}: {definition}" if part_of_speech else definition
        else:
            meaning = "Meaning not available."

        _MEANING_CACHE[word] = meaning
        return meaning

    except Exception:
        return "Meaning unavailable."