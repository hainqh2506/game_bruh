"""Đoán Chữ Unlimited — CLI: serve, warehouse, optional client snapshot."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx
import jsbeautifier

import db
from game.phrases import normalize_phrase
from paths import (
    BASE_URL,
    DATA_DIR,
    DEFAULT_PORT,
    PAGES_PROJECT,
    PUBLIC_DIR,
    ROOT,
    SOURCE_DIR,
    write,
)
from server.build import build_play
from server.runctl import stop_run
from server.serve import serve_play
from tools.warehouse import extract_open_source_dbs

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
        "--host",
        default=os.environ.get("HOST", "0.0.0.0"),
        help="Host interface to bind (default: 0.0.0.0 or env HOST)",
    )
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
    parser.add_argument(
        "--import-vdict",
        action="store_true",
        help="Add VDict 2-word headwords to Raw and Play (run/vdict/words.txt)",
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
    if args.import_vdict:
        print(json.dumps(db.import_vdict(), ensure_ascii=False, indent=2))
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
        serve_play(args.port, tunnel=args.tunnel, reload=args.reload, host=args.host)
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
