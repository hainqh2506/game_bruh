"""Repo paths and small IO helpers shared by CLI, server, and warehouse."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source" / "client"
DATA_DIR = ROOT / "data"
PLAY_DIR = ROOT / "play"
PUBLIC_DIR = ROOT / "public"
VENDOR_DIR = ROOT / "vendor"
OPEN_SOURCE_DIR = DATA_DIR / "open-source"
RUN_DIR = ROOT / "run"
STATUS_PATH = RUN_DIR / "status.json"
LINK_PATH = RUN_DIR / "LINK.txt"

PAGES_PROJECT = "doan-chu-unlimited"
DEFAULT_PORT = 18765
LEGACY_PORTS = (8765,)
BASE_URL = "https://doanchu.vn"


def write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
        return
    path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
