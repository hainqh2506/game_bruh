"""Port of play/marks.js — evaluate guesses and pick answers from SQLite."""

from __future__ import annotations

import random
import re
import unicodedata
from typing import Any

import db

TONE = {
    "\u0301": "acute",
    "\u0300": "grave",
    "\u0309": "hook",
    "\u0303": "tilde",
    "\u0323": "dot",
}
VOWEL_BASES = "aăâeêioôơuưy"
VIET_LETTER_RE = re.compile(r"[a-zA-ZÀ-ỹ]")
MAX_ATTEMPTS = 6


def decompose(ch: str) -> dict[str, str]:
    nfd = unicodedata.normalize("NFD", ch or "")
    tone = "none"
    base = ""
    for c in nfd:
        if c in TONE:
            tone = TONE[c]
        else:
            base += c
    return {"b": unicodedata.normalize("NFC", base).lower(), "t": tone}


def mark_guess(guess: str, answer: str) -> list[str | None]:
    guess = unicodedata.normalize("NFC", str(guess or ""))
    answer = unicodedata.normalize("NFC", str(answer or ""))
    n = len(answer)
    marks: list[str | None] = [None] * n
    used = [False] * n

    def is_space(i: int) -> bool:
        return i < n and answer[i] == " "

    for i in range(n):
        if is_space(i):
            continue
        if i < len(guess) and guess[i] == answer[i]:
            marks[i] = "green"
            used[i] = True
    for i in range(n):
        if is_space(i) or marks[i]:
            continue
        gi = guess[i] if i < len(guess) else ""
        for j in range(n):
            if used[j] or is_space(j):
                continue
            if gi == answer[j]:
                marks[i] = "yellow"
                used[j] = True
                break
    for i in range(n):
        if is_space(i) or marks[i]:
            continue
        gi = guess[i] if i < len(guess) else ""
        g = decompose(gi)
        if g["b"] not in VOWEL_BASES:
            continue
        for j in range(n):
            if used[j] or is_space(j):
                continue
            a = decompose(answer[j])
            if g["b"] == a["b"] and g["t"] != a["t"]:
                marks[i] = "blue"
                used[j] = True
                break
    for i in range(n):
        if is_space(i):
            marks[i] = None
        elif not marks[i]:
            marks[i] = "grey"
    return marks


def is_playable(guess: str, answer: str) -> bool:
    guess = unicodedata.normalize("NFC", str(guess or ""))
    answer = unicodedata.normalize("NFC", str(answer or ""))
    if len(guess) != len(answer):
        return False
    space = answer.find(" ")
    if space < 0 or guess.find(" ") != space:
        return False
    for i, ch in enumerate(answer):
        if i == space:
            if guess[i] != " ":
                return False
            continue
        if guess[i] == " " or not VIET_LETTER_RE.search(guess[i]):
            return False
    return True


def normalize_settings(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    words = int(raw.get("words") or 2)
    words = max(1, min(4, words))
    lengths = list(raw.get("lengths") or [])
    out = []
    for i in range(words):
        val = lengths[i] if i < len(lengths) else None
        try:
            n = int(val) if val is not None else None
        except (TypeError, ValueError):
            n = None
        out.append(n if n and n > 0 else None)
    rounds = int(raw.get("rounds") or 1)
    rounds = max(1, min(20, rounds))
    time_limit = max(0, int(raw.get("time_limit") or 0))
    return {"words": words, "lengths": out, "rounds": rounds, "time_limit": time_limit}


def matches_settings(phrase: str, settings: dict[str, Any]) -> bool:
    parts = unicodedata.normalize("NFC", phrase).strip().lower().split()
    if len(parts) != settings["words"]:
        return False
    for i, word in enumerate(parts):
        want = settings["lengths"][i]
        if want is not None and len(word) != want:
            return False
    return True


def pick_answer(settings: dict[str, Any] | None = None, rng: random.Random | None = None) -> str:
    cfg = normalize_settings(settings)
    phrases = db.all_phrases("play")
    pool = [p for p in phrases if matches_settings(p, cfg)]
    src = pool or phrases
    if not src:
        raise RuntimeError("Kho Play trống")
    pick = rng.choice if rng else random.choice
    return unicodedata.normalize("NFC", pick(src)).lower()


def puzzle_meta(answer: str) -> dict[str, int]:
    answer = unicodedata.normalize("NFC", answer)
    return {"length": len(answer), "spaceIndex": answer.find(" ")}
