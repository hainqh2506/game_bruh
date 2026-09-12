"""Normalize Vietnamese 2-word phrases (CLI, warehouse, debug API)."""

from __future__ import annotations

import re
import unicodedata

VIET_WORD_RE = re.compile(
    r"^[a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+$",
    re.IGNORECASE,
)


def normalize_phrase(text: str) -> str | None:
    text = unicodedata.normalize("NFC", text).strip().lower()
    parts = text.split()
    if len(parts) != 2:
        return None
    if not all(VIET_WORD_RE.fullmatch(part) and 1 <= len(part) <= 8 for part in parts):
        return None
    return f"{parts[0]} {parts[1]}"
