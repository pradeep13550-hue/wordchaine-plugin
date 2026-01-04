# Ultroid WordChain Auto Player (Advanced Offline Logic)
# Uses words.txt | No APIs | No auto-join | Group-safe

import re
import random
import asyncio
import hashlib
from pathlib import Path
from collections import defaultdict

from ultroid import events

GAME_BOT = "on9wordchainbot"

# ================= LOAD WORDS =================

WORDS_FILE = Path("resources/words.txt")
WORDS_BY_LETTER = defaultdict(list)

if WORDS_FILE.exists():
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            w = line.strip().lower()
            if w.isalpha() and len(w) >= 3:
                WORDS_BY_LETTER[w[0]].append(w)

# ================= CONSTANTS =================

STOPWORDS = {
    "your", "turn", "player", "selected",
    "minimum", "maximum", "word", "length", "letters"
}

GOOD_ENDINGS = set("aenrstl")
BAD_ENDINGS = set("qxzj")

# Per-chat memory
LAST_TURN_HASH = {}
USED_WORDS = defaultdict(set)

# ================= HELPERS =================

def extract_last_word(text: str):
    words = re.findall(r"\b[a-z]{3,}\b", text)
    words = [w for w in words if w not in STOPWORDS]
    return words[-1] if words else None


def extract_limits(text: str):
    min_len, max_len = 4, 12

    if m := re.search(r"min(?:imum)?\s*(\d+)", text):
        min_len = int(m.group(1))
    if m := re.search(r"max(?:imum)?\s*(\d+)", text):
        max_len = int(m.group(1))

    if m := re.search(r"(\d+)\s*(?:-|to)\s*(\d+)", text):
        min_len, max_len = int(m.group(1)), int(m.group(2))

    return min_len, max_len


def score_word(word: str) -> int:
    score = 0
    if word[-1] in GOOD_ENDINGS:
        score += 2
    if word[-1] in BAD_ENDINGS:
        score -= 2
    score += len(word) // 4  # slight preference for longer words
    return score


def choose_best_word(chat_id, letter, min_len, max_len):
    candidates = [
        w for w in WORDS_BY_LETTER.get(letter, [])
        if min_len <= len(w) <= max_len
        and w not in USED_WORDS[chat_id]
    ]

    if not candidates:
        return None

    # Rank words instead of pure random
    candidates.sort(key=score_word, reverse=True)

    # Choose from top few to avoid predictability
    top = candidates[:5] if len(candidates) >= 5 else candidates
    return random.choice(top)


def turn_hash(chat_id, text):
    return hashlib.sha1(f"{chat_id}:{text}".encode()).hexdigest()

# ================= MAIN HANDLER =================

@events.NewMessage(incoming=True)
async def wordchain_handler(event):
    sender = await event.get_sender()
    if not sender or sender.username != GAME_BOT:
        return

    if not WORDS_BY_LETTER:
        return  # words.txt missing or empty

    text = (event.text or "").lower()

    # Strict turn detection
    if not (
        "your turn" in text
        or "player selected" in text
    ):
        return

    h = turn_hash(event.chat_id, text)
    if LAST_TURN_HASH.get(event.chat_id) == h:
        return

    last_word = extract_last_word(text)
    if not last_word:
        return

    letter = last_word[-1]
    min_len, max_len = extract_limits(text)

    await asyncio.sleep(random.randint(2, 4))

    word = choose_best_word(event.chat_id, letter, min_len, max_len)
    if not word:
        return

    await event.reply(word)

    USED_WORDS[event.chat_id].add(word)
    LAST_TURN_HASH[event.chat_id] = h
