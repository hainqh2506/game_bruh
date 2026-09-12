"""Process flags."""

from __future__ import annotations

import os

from paths import load_dotenv

load_dotenv()


def debug_enabled() -> bool:
    return os.environ.get("DOANCHU_DEBUG", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
