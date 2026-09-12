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


def parse_import_lines(text: str) -> dict[str, list[str]]:
    """Parse a pasted/file list: one phrase per line, or word1,word2 CSV."""
    valid: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().replace(" ", "") in {"phrase", "cụmtừ", "cumtu"}:
            continue
        candidate = line
        if "," in line and " " not in line.split(",", 1)[0]:
            parts = [part.strip() for part in line.split(",") if part.strip()]
            if len(parts) >= 2:
                candidate = f"{parts[0]} {parts[1]}"
        norm = normalize_phrase(candidate)
        if not norm:
            invalid.append(line)
            continue
        if norm in seen:
            continue
        seen.add(norm)
        valid.append(norm)
    return {"valid": valid, "invalid": invalid}
