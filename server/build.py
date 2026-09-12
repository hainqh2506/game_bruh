"""Patch source/client HTML into public/ play bundle."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import db
from paths import DATA_DIR, PLAY_DIR, PUBLIC_DIR, SOURCE_DIR, VENDOR_DIR, write

# Append here when adding a play/*.js or *.css — build + reload pick them up.
PLAY_STYLES = ("debug.css", "settings.css", "room.css")
PLAY_SCRIPTS = ("phrases.js", "marks.js", "room.js", "mock.js", "debug.js")
PLAY_OPTIONAL = ("reload.js",)


def debug_watch_files() -> tuple[Path, ...]:
    names = [n for n in (*PLAY_STYLES, *PLAY_SCRIPTS, *PLAY_OPTIONAL) if n != "phrases.js"]
    return tuple(PLAY_DIR / name for name in names) + (SOURCE_DIR / "index.original.html",)


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
        from tools.warehouse import extract_open_source_dbs

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
    style_tags = "".join(f'<link rel="stylesheet" href="{name}"/>' for name in PLAY_STYLES)
    out = out.replace("</title>", f"</title>{style_tags}", 1)
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
    script_tags = "".join(f'<script src="{name}"></script>' for name in PLAY_SCRIPTS)
    if reload:
        script_tags += '<script src="reload.js"></script>'
    out = out.replace(needle, script_tags + needle, 1)
    dest = PLAY_DIR / "index.html"
    write(dest, out)

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    write(PUBLIC_DIR / "index.html", out)
    for name in (*PLAY_STYLES, *PLAY_SCRIPTS, *PLAY_OPTIONAL):
        src = PLAY_DIR / name
        dest_pub = PUBLIC_DIR / name
        if name == "reload.js" and not reload:
            if dest_pub.exists():
                dest_pub.unlink()
            continue
        if src.exists():
            shutil.copy2(src, dest_pub)
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
