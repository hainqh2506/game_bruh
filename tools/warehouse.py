"""Rebuild SQLite from optional vendor clones (not needed for play; sqlite is shipped)."""

from __future__ import annotations

import json
import shutil

import db
from game.phrases import normalize_phrase
from paths import OPEN_SOURCE_DIR, VENDOR_DIR, write


def extract_open_source_dbs() -> dict:
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
