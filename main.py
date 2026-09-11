"""Đoán Chữ Unlimited — local/tunnel server, SQLite word pools, optional client snapshot."""

from __future__ import annotations

import argparse
import json
import os
import signal
import re
import shutil
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import jsbeautifier

import db

BASE_URL = "https://doanchu.vn"
ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source" / "client"
DATA_DIR = ROOT / "data"
PLAY_DIR = ROOT / "play"
PUBLIC_DIR = ROOT / "public"
VENDOR_DIR = ROOT / "vendor"
OPEN_SOURCE_DIR = DATA_DIR / "open-source"
PAGES_PROJECT = "doan-chu-unlimited"
DEFAULT_PORT = 18765
RUN_DIR = ROOT / "run"
STATUS_PATH = RUN_DIR / "status.json"
LINK_PATH = RUN_DIR / "LINK.txt"
LEGACY_PORTS = (8765,)

VIET_WORD_RE = re.compile(
    r"^[a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+$",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Hex identifiers in the inline game script, longest first.
JS_RENAMES: list[tuple[str, str]] = [
    ("_0x4e", "CHAR_TO_BASE_TONE"),
    ("_0x5a", "BASE_TONE_TO_CHAR"),
    ("_0x1d", "VIET_CHARS"),
    ("_0x3c", "submitting"),
    ("_0x3b", "composeChar"),
    ("_0x3a", "initUi"),
    ("_0x39", "loadPuzzle"),
    ("_0x38", "setupPuzzle"),
    ("_0x37", "closeEndgame"),
    ("_0x36", "drawPreview"),
    ("_0x35", "showEndgame"),
    ("_0x34", "popupOpenedAt"),
    ("_0x33", "submitGuess"),
    ("_0x32", "copyText"),
    ("_0x31", "formatShareText"),
    ("_0x30", "previewCache"),
    ("_0x2f", "SHARE_COLORS"),
    ("_0x2e", "bindKeyboard"),
    ("_0x2d", "buildKeyboard"),
    ("_0x2c", "decomposeChar"),
    ("_0x2b", "keyboardBound"),
    ("_0x2a", "backspace"),
    ("_0x29", "typeKey"),
    ("_0x28", "setCurrent"),
    ("_0x27", "applyVowelKey"),
    ("_0x26", "applyKey"),
    ("_0x25", "TONE_KEYS"),
    ("_0x24", "cursorIndex"),
    ("_0x23", "renderBoard"),
    ("_0x22", "restoreFromStorage"),
    ("_0x21", "syncGameOverUi"),
    ("_0x20", "getGameStatus"),
    ("_0x1f", "rebuildResults"),
    ("_0x1e", "pruneOldSaves"),
    ("_0x1c", "scheduleSave"),
    ("_0x1b", "makeStorageKey"),
    ("_0x1a", "findTonePosition"),
    ("_0x19", "insertSpace"),
    ("_0x18", "stripSpaces"),
    ("_0x17", "lastKeyTime"),
    ("_0x16", "lastKey"),
    ("_0x15", "word1ToneWindowUntil"),
    ("_0x14", "saveTimer"),
    ("_0x13", "boardLength"),
    ("_0x12", "storageKey"),
    ("_0x11", "puzzleDate"),
    ("_0x10", "solvedAnswer"),
    ("_0x0f", "spaceIndex"),
    ("_0x0e", "popupOpen"),
    ("_0x0d", "gameOver"),
    ("_0x0c", "shareState"),
    ("_0x0b", "resultsGrid"),
    ("_0x0a", "MAX_ATTEMPTS"),
    ("_0x09", "currentInput"),
    ("_0x08", "marksList"),
    ("_0x07", "guesses"),
    ("_0x06", "stickyShareEl"),
    ("_0x05", "lengthInfoEl"),
    ("_0x04", "lenHintEl"),
    ("_0x03", "keyboardEl"),
    ("_0x02", "messageEl"),
    ("_0x01", "rowsEl"),
    ("_0x41", "applyTone"),
]

PUBLIC_ASSETS = [
    "/images/doanchu-logo.png",
    "/images/favicon-16x16.png",
    "/images/favicon-32x32.png",
    "/images/favicon.ico",
    "/images/apple-touch-icon.png",
    "/images/site.webmanifest",
]


def fetch_text(client: httpx.Client, path: str) -> tuple[int, str, str]:
    res = client.get(path)
    return res.status_code, res.headers.get("content-type", ""), res.text


def fetch_bytes(client: httpx.Client, path: str) -> tuple[int, bytes]:
    res = client.get(path)
    return res.status_code, res.content


def extract_inline_css(html: str) -> str:
    match = re.search(r"<style>(.*?)</style>", html, flags=re.S | re.I)
    return match.group(1).strip() if match else ""


def extract_game_js(html: str) -> str:
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S | re.I)
    if not scripts:
        return ""
    return max(scripts, key=len).strip()


def beautify_js(source: str) -> str:
    opts = jsbeautifier.default_options()
    opts.indent_size = 2
    opts.preserve_newlines = False
    return jsbeautifier.beautify(source, opts)


VIET_CHAR_TABLE = [
    "a", "á", "à", "ạ", "ả", "ã",
    "ă", "ắ", "ằ", "ặ", "ẳ", "ẵ",
    "â", "ấ", "ầ", "ậ", "ẩ", "ẫ",
    "e", "é", "è", "ẹ", "ẻ", "ẽ",
    "ê", "ế", "ề", "ệ", "ể", "ễ",
    "i", "í", "ì", "ị", "ỉ", "ĩ",
    "o", "ó", "ò", "ọ", "ỏ", "õ",
    "ô", "ố", "ồ", "ộ", "ổ", "ỗ",
    "ơ", "ớ", "ờ", "ợ", "ở", "ỡ",
    "u", "ú", "ù", "ụ", "ủ", "ũ",
    "ư", "ứ", "ừ", "ự", "ử", "ữ",
    "y", "ý", "ỳ", "ỵ", "ỷ", "ỹ",
    "đ", "none", "acute", "grave", "dot", "hook", "tilde",
]


def deobfuscate_js(pretty: str) -> str:
    out = pretty
    for old, new in JS_RENAMES:
        out = re.sub(rf"\b{re.escape(old)}\b", new, out)
    for index, char in enumerate(VIET_CHAR_TABLE):
        out = out.replace(f"VIET_CHARS[{index}]", json.dumps(char, ensure_ascii=False))
    header = (
        "/*\n"
        " * Client game logic extracted from https://doanchu.vn/ (V3).\n"
        " * Hex identifiers renamed for readability. Behavior is unchanged.\n"
        " * Puzzle answers and the valid-word dictionary are NOT in this file;\n"
        " * they are served by getWord.php / checkGuess.php on the server.\n"
        " */\n"
    )
    return header + out


def write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
        if not content.endswith("\n"):
            path.write_text(content + "\n", encoding="utf-8")


def architecture_report(puzzle: dict) -> dict:
    return {
        "site": BASE_URL,
        "version": "V3",
        "gemini_claim": (
            "Game is fully client-side; answers live in a JS array indexed by date."
        ),
        "actual_architecture": "hybrid-client-ui-plus-php-backend",
        "client_contains": [
            "UI (HTML/CSS)",
            "Vietnamese Telex input (s/f/r/x/j/z tones, w for ă/ơ/ư)",
            "Board rendering and keyboard",
            "localStorage progress keyed as doanchu:v3:YYYY-MM-DD",
            "Share text + canvas export",
        ],
        "server_endpoints": {
            "getWord.php": {
                "method": "GET",
                "role": "Daily puzzle metadata",
                "observed_response": puzzle,
                "leaks_answer": "answer" in puzzle,
            },
            "checkGuess.php": {
                "method": "POST",
                "body": {"guess": "<typed phrase>", "attempt": "<1-6>"},
                "role": (
                    "Validates the guess against the server dictionary, "
                    "returns color marks, won flag, and solution after the game ends"
                ),
            },
            "logResult.php": {
                "method": "POST",
                "role": "Telemetry: won + number of guesses",
            },
        },
        "database_location": (
            "Not in client JS. Answers and valid phrases are on the PHP server. "
            "Public files words.json / dictionary.json / answers.json return 404."
        ),
        "why_date_override_does_not_unlock_unlimited_mode": (
            "The daily word is chosen by getWord.php, not by Date.now() in the browser. "
            "Clearing localStorage only lets you replay today's server-chosen phrase."
        ),
        "today_puzzle": puzzle,
        "mark_colors": {
            "green": "correct letter + tone, correct position",
            "yellow": "correct letter + tone, wrong position",
            "blue": "same vowel base, wrong tone (position not guaranteed)",
            "grey": "absent",
        },
        "localStorage_schema": {
            "key": "doanchu:v3:{date}",
            "value": {
                "version": 3,
                "date": "YYYY-MM-DD",
                "len": "board length including the space slot",
                "spaceIndex": "index of the gap between the two words",
                "guesses": ["..."],
                "marksList": [["green|yellow|blue|grey", "..."]],
                "current": "in-progress input",
                "solvedAnswer": "filled after win/loss if server sent solution",
            },
        },
    }


def fetch_live() -> tuple[str, dict]:
    with httpx.Client(
        base_url=BASE_URL,
        headers=HEADERS,
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        status, _, html = fetch_text(client, "/")
        if status != 200:
            raise SystemExit(f"Failed to fetch homepage: HTTP {status}")

        puzzle_status, _, puzzle_raw = fetch_text(client, "/getWord.php")
        puzzle = json.loads(puzzle_raw) if puzzle_status == 200 else {"error": puzzle_raw}

        for asset in PUBLIC_ASSETS:
            code, blob = fetch_bytes(client, asset)
            if code == 200:
                write(SOURCE_DIR / asset.lstrip("/"), blob)

    return html, puzzle


def save_snapshot(html: str, puzzle: dict) -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    css = extract_inline_css(html)
    raw_js = extract_game_js(html)
    pretty_js = beautify_js(raw_js)
    deobf_js = deobfuscate_js(pretty_js)
    report = architecture_report(puzzle)

    write(SOURCE_DIR / "index.original.html", html)
    write(SOURCE_DIR / "styles.css", css)
    write(SOURCE_DIR / "game.raw.js", raw_js)
    write(SOURCE_DIR / "game.pretty.js", pretty_js)
    write(SOURCE_DIR / "game.deobfuscated.js", deobf_js)
    write(DATA_DIR / "puzzle_today.json", json.dumps(puzzle, ensure_ascii=False, indent=2))
    write(DATA_DIR / "architecture.json", json.dumps(report, ensure_ascii=False, indent=2))
    return css, raw_js, pretty_js


def normalize_phrase(text: str) -> str | None:
    text = unicodedata.normalize("NFC", text).strip().lower()
    parts = text.split()
    if len(parts) != 2:
        return None
    if not all(VIET_WORD_RE.fullmatch(part) and 1 <= len(part) <= 8 for part in parts):
        return None
    return f"{parts[0]} {parts[1]}"


def extract_open_source_dbs() -> dict:
    """Copy cloned GitHub word DBs and emit a combined 2-word phrase list."""
    wordlist_src = VENDOR_DIR / "vietnamese-wordlist"
    noitu_src = VENDOR_DIR / "noitu" / "assets" / "wordPairs.json"
    if not wordlist_src.exists() or not noitu_src.exists():
        raise SystemExit(
            "Missing vendor clones. Run:\n"
            "  git clone --depth 1 https://github.com/duyet/vietnamese-wordlist.git vendor/vietnamese-wordlist\n"
            "  git clone --depth 1 https://github.com/minhqnd/noitu.git vendor/noitu"
        )

    dest_wl = OPEN_SOURCE_DIR / "vietnamese-wordlist"
    dest_noitu = OPEN_SOURCE_DIR / "noitu"
    dest_wl.mkdir(parents=True, exist_ok=True)
    dest_noitu.mkdir(parents=True, exist_ok=True)

    copied = []
    for name in ["Viet11K.txt", "Viet22K.txt", "Viet39K.txt", "Viet74K.txt", "LICENSE", "README.md"]:
        src = wordlist_src / name
        if src.exists():
            shutil.copy2(src, dest_wl / name)
            copied.append(str(dest_wl / name))
    shutil.copy2(noitu_src, dest_noitu / "wordPairs.json")
    copied.append(str(dest_noitu / "wordPairs.json"))
    noitu_license = VENDOR_DIR / "noitu" / "LICENSE"
    if noitu_license.exists():
        shutil.copy2(noitu_license, dest_noitu / "LICENSE")

    phrases: dict[str, list[str]] = {}
    for name in ["Viet11K.txt", "Viet22K.txt", "Viet39K.txt", "Viet74K.txt"]:
        for line in (dest_wl / name).read_text(encoding="utf-8").splitlines():
            phrase = normalize_phrase(line)
            if phrase:
                phrases.setdefault(phrase, []).append(name)

    pairs = json.loads(noitu_src.read_text(encoding="utf-8"))
    noitu_count = 0
    for first, seconds in pairs.items():
        if not isinstance(seconds, list):
            continue
        for second in seconds:
            phrase = normalize_phrase(f"{first} {second}")
            if phrase:
                phrases.setdefault(phrase, []).append("noitu")
                noitu_count += 1

    combined = sorted(phrases)
    rows = [
        (phrase, ",".join(dict.fromkeys(sources)))
        for phrase, sources in sorted(phrases.items())
    ]
    sqlite_count = db.import_raw(rows)
    filter_stats = db.filter_vulgar()
    seed_stats = db.seed_play_if_empty()
    artifacts = db.export_artifacts()
    stats = {
        "vietnamese-wordlist_files": copied[:5],
        "noitu_pairs_kept": noitu_count,
        "unique_two_word_phrases": len(combined),
        "imported_raw": sqlite_count,
        "filter": filter_stats,
        "seed": seed_stats,
        "sqlite": artifacts["sqlite"],
        "phrases_json": artifacts["json"],
        "phrases_js": artifacts["js"],
        "play": artifacts["play"],
        "raw": artifacts["raw"],
        "rejected": artifacts["rejected"],
    }
    write(OPEN_SOURCE_DIR / "manifest.json", json.dumps(stats, ensure_ascii=False, indent=2))
    return stats


def debug_enabled() -> bool:
    return os.environ.get("DOANCHU_DEBUG", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def ensure_phrases_js() -> Path:
    dest = PLAY_DIR / "phrases.js"
    src_json = DATA_DIR / "phrases_two_words.json"
    db.connect().close()
    if db.count() > 0:
        if db.count("play") == 0:
            db.filter_vulgar()
            db.seed_play_if_empty()
        return Path(db.export_artifacts()["js"])
    if (VENDOR_DIR / "vietnamese-wordlist").exists() and not src_json.exists():
        extract_open_source_dbs()
        return PLAY_DIR / "phrases.js"
    if src_json.exists():
        phrases = json.loads(src_json.read_text(encoding="utf-8"))
        db.import_raw([(p, "json") for p in phrases])
        db.filter_vulgar()
        db.seed_play_if_empty()
        return Path(db.export_artifacts()["js"])
    if dest.exists():
        return dest
    raise SystemExit(
        "No phrase list. Clone the GitHub DBs then run: uv run python main.py --extract-db"
    )


WATCH_PLAY_FILES = (
    PLAY_DIR / "mock.js",
    PLAY_DIR / "marks.js",
    PLAY_DIR / "debug.js",
    PLAY_DIR / "debug.css",
    PLAY_DIR / "settings.css",
    PLAY_DIR / "reload.js",
    SOURCE_DIR / "index.original.html",
)


def build_play(
    html: str | None = None,
    *,
    reload: bool = False,
    refresh_phrases: bool = True,
) -> Path:
    """Patch the public client into a local unlimited game (no PHP)."""
    if refresh_phrases or not (PLAY_DIR / "phrases.js").exists():
        ensure_phrases_js()
    source_html = html or (SOURCE_DIR / "index.original.html").read_text(encoding="utf-8")
    if not (PLAY_DIR / "mock.js").exists():
        raise SystemExit("Missing play/mock.js")
    out = source_html
    out = re.sub(
        r'<script async src="https://www.googletagmanager.com/gtag/js\?id=AW-\d+"></script>',
        "",
        out,
    )
    out = re.sub(
        r"<script>window\.dataLayer=window\.dataLayer\|\|\[\];function gtag\(\)\{dataLayer\.push\(arguments\);\}gtag\(\"js\",new Date\(\)\);gtag\(\"config\",\"AW-\d+\"\);</script>",
        "",
        out,
    )
    out = re.sub(r'<link rel="manifest"[^>]*>', "", out)
    out = re.sub(r'<link rel="icon"[^>]*>', "", out)
    out = re.sub(r'<link rel="apple-touch-icon"[^>]*>', "", out)
    out = out.replace("<title>Đoán Chữ V3</title>", "<title>Đoán Chữ Unlimited</title>")
    out = out.replace(
        "</title>",
        '</title><link rel="stylesheet" href="debug.css"/><link rel="stylesheet" href="settings.css"/>',
        1,
    )
    out = re.sub(
        r'<h1 class="logo"><img src="/images/doanchu-logo.png"[^>]*/></h1>',
        '<h1 class="logo" style="font-size:clamp(22px,5vw,34px);font-weight:800;">Đoán Chữ Unlimited</h1>',
        out,
    )
    out = re.sub(
        r'<span id="contact-info">.*?</span>',
        '<span id="contact-info">Không giới hạn 1 từ / ngày</span>',
        out,
        count=1,
    )
    out = re.sub(r'<a href="/mecungchu/" class="desktop-crossword-link">.*?</a>', "", out)
    out = re.sub(r'<a href="/mecungchu/" class="mobile-crossword-banner">.*?</a>', "", out)
    out = out.replace(
        '<button id="sticky-share" class="sticky-share" type="button" hidden>Chia sẻ</button>',
        '<button id="new-game" class="sticky-share" type="button">Ván mới</button>'
        '<button id="sticky-share" class="sticky-share" type="button" hidden>Chia sẻ</button>',
    )
    needle = "<script>\n(()=>{"
    if needle not in out:
        needle = "<script>(()=>{"
    if needle not in out:
        raise SystemExit("Could not find the game script to inject unlimited mode")
    reload_tag = '<script src="reload.js"></script>' if reload else ""
    out = out.replace(
        needle,
        '<script src="phrases.js"></script>'
        '<script src="marks.js"></script>'
        '<script src="mock.js"></script>'
        '<script src="debug.js"></script>'
        + reload_tag
        + needle,
        1,
    )
    dest = PLAY_DIR / "index.html"
    write(dest, out)

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    write(PUBLIC_DIR / "index.html", out)
    shutil.copy2(PLAY_DIR / "phrases.js", PUBLIC_DIR / "phrases.js")
    shutil.copy2(PLAY_DIR / "marks.js", PUBLIC_DIR / "marks.js")
    shutil.copy2(PLAY_DIR / "mock.js", PUBLIC_DIR / "mock.js")
    shutil.copy2(PLAY_DIR / "debug.js", PUBLIC_DIR / "debug.js")
    shutil.copy2(PLAY_DIR / "debug.css", PUBLIC_DIR / "debug.css")
    shutil.copy2(PLAY_DIR / "settings.css", PUBLIC_DIR / "settings.css")
    if reload and (PLAY_DIR / "reload.js").exists():
        shutil.copy2(PLAY_DIR / "reload.js", PUBLIC_DIR / "reload.js")
    else:
        leftover = PUBLIC_DIR / "reload.js"
        if leftover.exists():
            leftover.unlink()
    write(
        PUBLIC_DIR / "_headers",
        "\n".join(
            [
                "/*",
                "  X-Content-Type-Options: nosniff",
                "  Referrer-Policy: strict-origin-when-cross-origin",
                "",
                "/phrases.js",
                "  Cache-Control: public, max-age=3600",
                "",
            ]
        ),
    )
    write(
        PUBLIC_DIR / "404.html",
        '<!DOCTYPE html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/">'
        "<title>Not found</title><p><a href=\"/\">Về trang chơi</a></p>\n",
    )
    return dest


def write_run_status(**fields: object) -> dict:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if STATUS_PATH.exists():
        try:
            data = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    data.update(fields)
    data["updated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    public = data.get("public_url") or "(đang tạo tunnel…)"
    debug = "ON" if data.get("debug") else "OFF"
    reload_on = "ON" if data.get("reload") else "OFF"
    LINK_PATH.write_text(
        "\n".join(
            [
                "Đoán Chữ Unlimited",
                "",
                f"Public:  {public}",
                f"Local:   {data.get('local_url', '')}",
                f"Port:    {data.get('port', '')}",
                f"Debug:   {debug}",
                f"Reload:  {reload_on}",
                f"Python:  pid {data.get('python_pid', '')}",
                f"Tunnel:  pid {data.get('tunnel_pid', '') or '-'}",
                f"Updated: {data.get('updated_at', '')}",
                "",
                "Sửa play/*.js rồi đợi trang tự F5 — không chạy lại make dev.",
                "Tắt:  uv run python main.py --stop",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return data


def _kill_pid(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        return


def stop_run(extra_ports: tuple[int, ...] = ()) -> None:
    import subprocess

    ports: set[int] = set(extra_ports)
    pids: set[int] = set()
    if STATUS_PATH.exists():
        try:
            data = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if data.get("port"):
            ports.add(int(data["port"]))
        for key in ("python_pid", "tunnel_pid"):
            if data.get(key):
                pids.add(int(data[key]))
    ports.update(LEGACY_PORTS)
    for pid in pids:
        _kill_pid(pid)
    for port in ports:
        subprocess.run(
            ["fuser", "-k", f"{port}/tcp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    subprocess.run(
        ["pkill", "-f", "cloudflared tunnel --no-autoupdate --url http://127.0.0.1:"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if STATUS_PATH.exists() or LINK_PATH.exists():
        write_run_status(public_url="", python_pid="", tunnel_pid="", stopped=True)
    print("Đã tắt server/tunnel cũ.", flush=True)


class ReloadState:
    def __init__(self) -> None:
        self.generation = 0
        self.cond = threading.Condition()

    def bump(self) -> int:
        with self.cond:
            self.generation += 1
            self.cond.notify_all()
            return self.generation

    def wait_after(self, seen: int, timeout: float = 25.0) -> int:
        with self.cond:
            if self.generation > seen:
                return self.generation
            self.cond.wait(timeout=timeout)
            return self.generation


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def watch_play_files(state: ReloadState) -> None:
    import time

    files = list(WATCH_PLAY_FILES)
    mtimes = {path: _mtime(path) for path in files}
    print(
        "Reload: ON — sửa play/mock.js, debug.js, debug.css; trang tự F5, tunnel giữ nguyên.",
        flush=True,
    )
    while True:
        time.sleep(0.35)
        changed = [path.name for path in files if _mtime(path) != mtimes[path]]
        if not changed:
            continue
        time.sleep(0.15)
        mtimes = {path: _mtime(path) for path in files}
        try:
            build_play(reload=True, refresh_phrases=False)
            gen = state.bump()
            print(f"Reloaded #{gen}: {', '.join(changed)}", flush=True)
        except Exception as exc:
            print(f"Reload failed: {exc}", flush=True)


def serve_play(port: int = DEFAULT_PORT, tunnel: bool = False, reload: bool = True) -> None:
    import http.server
    import socketserver
    import subprocess
    import webbrowser

    build_play(reload=reload)
    on = debug_enabled()
    state = ReloadState()
    TUNNEL_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

    class ReuseTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True
        block_on_close = False

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

        def log_message(self, format: str, *args) -> None:
            print("%s - %s" % (self.address_string(), format % args), flush=True)

        def end_headers(self) -> None:
            if reload:
                self.send_header("Cache-Control", "no-store")
                self.send_header("Pragma", "no-cache")
            super().end_headers()

        def _json(self, payload: dict, status: int = 200) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8") or "{}")

        def _require_debug(self) -> bool:
            if on:
                return True
            self._json({"error": "debug disabled"}, 403)
            return False

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/reload":
                if not reload:
                    self.send_error(404)
                    return
                qs = parse_qs(parsed.query)
                try:
                    seen = int((qs.get("gen") or ["0"])[0] or 0)
                except ValueError:
                    seen = 0
                self._json({"generation": state.wait_after(seen)})
                return
            if parsed.path == "/api/config":
                payload = {"debug": on}
                if on:
                    payload["counts"] = db.counts()
                self._json(payload)
                return
            if parsed.path == "/api/phrases":
                if not self._require_debug():
                    return
                qs = parse_qs(parsed.query)
                query = (qs.get("q") or [""])[0]
                pool = (qs.get("pool") or ["play"])[0]
                page = int((qs.get("page") or ["1"])[0] or 1)
                limit = int((qs.get("limit") or ["50"])[0] or 50)
                self._json(db.search(query, page, limit, pool))
                return
            super().do_GET()

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/api/phrases" or not self._require_debug():
                if parsed.path != "/api/phrases":
                    self.send_error(404)
                return
            body = self._read_json()
            phrase = normalize_phrase(str(body.get("phrase") or ""))
            pool = str(body.get("pool") or "play")
            if not phrase:
                self._json({"error": "Cần cụm đúng 2 từ tiếng Việt"}, 400)
                return
            created = db.add_phrase(phrase, source="manual", pool=pool)
            db.export_artifacts()
            self._json({"ok": True, "created": created, "phrase": phrase, "counts": db.counts()})

        def do_PATCH(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/api/phrases" or not self._require_debug():
                if parsed.path != "/api/phrases":
                    self.send_error(404)
                return
            body = self._read_json()
            phrase = normalize_phrase(str(body.get("phrase") or "")) or str(body.get("phrase") or "").strip().lower()
            pool = str(body.get("pool") or "")
            if not phrase or pool not in db.POOLS:
                self._json({"error": "phrase/pool không hợp lệ"}, 400)
                return
            ok = db.set_pool(phrase, pool)
            db.export_artifacts()
            self._json({"ok": ok, "phrase": phrase, "pool": pool, "counts": db.counts()}, 200 if ok else 404)

        def do_DELETE(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/api/phrases" or not self._require_debug():
                if parsed.path != "/api/phrases":
                    self.send_error(404)
                return
            body = self._read_json()
            phrase = normalize_phrase(str(body.get("phrase") or "")) or str(body.get("phrase") or "").strip().lower()
            pool = body.get("pool")
            ok = db.remove_phrase(phrase, pool if pool in db.POOLS else None)
            db.export_artifacts()
            self._json({"ok": ok, "counts": db.counts()}, 200 if ok else 404)

    tunnel_proc: subprocess.Popen | None = None

    def run_quick_tunnel() -> None:
        nonlocal tunnel_proc
        cmd = [
            "cloudflared",
            "tunnel",
            "--no-autoupdate",
            "--url",
            f"http://127.0.0.1:{port}",
        ]
        print("Starting Cloudflare Quick Tunnel (no login)…", flush=True)
        tunnel_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert tunnel_proc.stdout is not None
        public = None
        for line in tunnel_proc.stdout:
            print(line.rstrip(), flush=True)
            match = TUNNEL_URL_RE.search(line)
            if match and public is None:
                public = match.group(0)
                write_run_status(public_url=public, tunnel_pid=tunnel_proc.pid)
                print("\n========================================", flush=True)
                print(f"  Gửi link này: {public}", flush=True)
                print(f"  Đã ghi: {LINK_PATH}", flush=True)
                print("========================================\n", flush=True)

    try:
        httpd_cm = ReuseTCPServer(("127.0.0.1", port), Handler)
    except OSError as exc:
        if getattr(exc, "errno", None) == 98:
            raise SystemExit(
                f"Cổng {port} đang bị chiếm (server lần trước chưa tắt).\n"
                f"Tắt bằng:  fuser -k {port}/tcp\n"
                f"Hoặc cổng khác:  uv run python main.py --tunnel --port {port + 1}"
            ) from exc
        raise

    with httpd_cm as httpd:
        url = f"http://127.0.0.1:{port}/"
        write_run_status(
            local_url=url,
            public_url="",
            port=port,
            debug=on,
            reload=reload,
            python_pid=os.getpid(),
            tunnel_pid="",
            stopped=False,
        )
        print(f"Local: {url}", flush=True)
        print(f"Debug tab: {'ON' if on else 'OFF'}  (DOANCHU_DEBUG=1 to enable)", flush=True)
        print(f"Reload: {'ON' if reload else 'OFF'}  (--no-reload to disable)", flush=True)
        print(f"Status file: {LINK_PATH}", flush=True)
        if reload:
            threading.Thread(target=watch_play_files, args=(state,), daemon=True).start()
        if tunnel:
            threading.Thread(target=run_quick_tunnel, daemon=True).start()
        else:
            print("Friends: uv run python main.py --tunnel", flush=True)
            try:
                webbrowser.open(url)
            except Exception:
                pass
        try:
            httpd.serve_forever()
        finally:
            if tunnel_proc and tunnel_proc.poll() is None:
                tunnel_proc.terminate()


def deploy_cloudflare() -> None:
    import subprocess

    build_play()
    cmd = [
        "npx",
        "--yes",
        "wrangler",
        "pages",
        "deploy",
        str(PUBLIC_DIR),
        "--project-name",
        PAGES_PROJECT,
        "--commit-dirty=true",
    ]
    print("Deploying to Cloudflare Pages:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(
            "Deploy failed. First time: npx wrangler login\n"
            "Then: uv run python main.py --deploy"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fetch-client",
        action="store_true",
        help="Download the public doanchu.vn client snapshot into source/client/",
    )
    parser.add_argument(
        "--html",
        type=Path,
        help="Use a local HTML snapshot instead of fetching the live site",
    )
    parser.add_argument(
        "--puzzle",
        type=Path,
        help="JSON from getWord.php (used with --html)",
    )
    parser.add_argument(
        "--build-play",
        action="store_true",
        help="Build local unlimited game at play/index.html",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Build and serve the local unlimited game",
    )
    parser.add_argument(
        "--tunnel",
        action="store_true",
        help="Serve locally and open a Cloudflare Quick Tunnel (no login)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=True,
        help="Watch play/ and auto-refresh the browser (default on with --serve/--tunnel)",
    )
    parser.add_argument(
        "--no-reload",
        action="store_false",
        dest="reload",
        help="Do not watch files or auto-refresh",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop the running local server / Quick Tunnel",
    )
    parser.add_argument(
        "--extract-db",
        action="store_true",
        help="Rebuild the phrase warehouse from optional vendor clones (not required; sqlite is shipped)",
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Build the static site and deploy to Cloudflare Pages",
    )
    parser.add_argument("--add-phrase", metavar="PHRASE", help="Add a 2-word phrase to SQLite")
    parser.add_argument("--remove-phrase", metavar="PHRASE", help="Remove a phrase from SQLite")
    parser.add_argument(
        "--pool",
        choices=list(db.POOLS),
        default="play",
        help="Target pool for --add-phrase (default: play)",
    )
    parser.add_argument(
        "--filter-vulgar",
        action="store_true",
        help="Move vulgar phrases from raw/play into rejected",
    )
    parser.add_argument(
        "--curate-play",
        action="store_true",
        help="Rebuild Play from Viet11K 2-word compounds (2–5 letters each)",
    )
    args = parser.parse_args()

    if args.stop:
        stop_run()
        return

    if args.filter_vulgar:
        print(json.dumps(db.filter_vulgar(), ensure_ascii=False, indent=2))
        db.export_artifacts()
        return
    if args.curate_play:
        print(json.dumps(db.curate_play(), ensure_ascii=False, indent=2))
        db.export_artifacts()
        return
    if args.add_phrase:
        phrase = normalize_phrase(args.add_phrase)
        if not phrase:
            raise SystemExit("Phrase must be exactly two Vietnamese words")
        ok = db.add_phrase(phrase, pool=args.pool)
        db.export_artifacts()
        print(("added " if ok else "moved/exists ") + phrase + f" → {args.pool}")
        print(json.dumps(db.counts(), ensure_ascii=False))
        return
    if args.remove_phrase:
        phrase = normalize_phrase(args.remove_phrase) or args.remove_phrase.strip().lower()
        ok = db.remove_phrase(phrase)
        db.export_artifacts()
        print(("removed " if ok else "not found ") + phrase)
        print(json.dumps(db.counts(), ensure_ascii=False))
        return
    if args.extract_db:
        stats = extract_open_source_dbs()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return
    if args.deploy:
        deploy_cloudflare()
        return
    if args.serve or args.tunnel:
        stop_run(extra_ports=(args.port,))
        serve_play(args.port, tunnel=args.tunnel, reload=args.reload)
        return
    if args.build_play:
        dest = build_play()
        print(f"Wrote {dest}")
        print(f"Cloudflare bundle: {PUBLIC_DIR}")
        print("Local:  uv run python main.py --serve")
        print("Deploy: uv run python main.py --deploy")
        return

    if not args.fetch_client and not args.html:
        parser.print_help()
        print("\nChơi ngay:  make dev")
        return

    if args.html:
        html = args.html.read_text(encoding="utf-8")
        if args.puzzle:
            puzzle = json.loads(args.puzzle.read_text(encoding="utf-8"))
        else:
            puzzle = {}
    else:
        html, puzzle = fetch_live()

    css, raw_js, pretty_js = save_snapshot(html, puzzle)

    print("Client source saved under source/client/")
    print(f"  HTML      {len(html):6d} bytes")
    print(f"  CSS       {len(css):6d} bytes")
    print(f"  JS raw    {len(raw_js):6d} bytes")
    print(f"  JS pretty {len(pretty_js):6d} bytes")
    print()
    print("Today's public puzzle metadata (getWord.php):")
    print(json.dumps(puzzle, ensure_ascii=False, indent=2))
    print()
    print("Database: not in the client.")
    print("  getWord.php does not return the answer — only date/length/spaceIndex.")
    print("  Valid phrases and the daily answer live on the PHP backend.")
    print("  Clearing localStorage or spoofing Date will not rotate the word.")


if __name__ == "__main__":
    main()
