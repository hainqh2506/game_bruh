"""SQLite warehouse: raw dump, curated play pool, rejected list."""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from pathlib import Path

from game.phrases import VIET_WORD_RE, normalize_phrase
from paths import DATA_DIR, PLAY_DIR, ROOT, VENDOR_DIR

DB_PATH = DATA_DIR / "words.sqlite"
VULGAR_PATH = DATA_DIR / "vulgar.txt"
WORDLIST_DIRS = (
    DATA_DIR / "open-source" / "vietnamese-wordlist",
    VENDOR_DIR / "vietnamese-wordlist",
)

POOLS = ("raw", "play", "rejected")
PLAY_MIN_WORD_LEN = 2
PLAY_MAX_WORD_LEN = 5

SCHEMA = """
CREATE TABLE IF NOT EXISTS phrases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phrase TEXT NOT NULL,
  word1 TEXT NOT NULL,
  word2 TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT '',
  letter_len INTEGER NOT NULL,
  space_index INTEGER NOT NULL,
  pool TEXT NOT NULL DEFAULT 'raw'
    CHECK (pool IN ('raw', 'play', 'rejected')),
  UNIQUE (phrase, pool)
);
CREATE INDEX IF NOT EXISTS idx_phrases_word1 ON phrases(word1);
CREATE INDEX IF NOT EXISTS idx_phrases_len ON phrases(letter_len);
CREATE INDEX IF NOT EXISTS idx_phrases_pool ON phrases(pool);
CREATE INDEX IF NOT EXISTS idx_phrases_phrase ON phrases(phrase);
CREATE TABLE IF NOT EXISTS vdict_words (
  phrase TEXT PRIMARY KEY
);
"""

DEFAULT_VULGAR = """
# Mỗi dòng một từ/cụm. Khớp nguyên word1, word2, hoặc cả cụm.
đụ
địt
lồn
cặc
buồi
đéo
đĩ
cứt
dái
loz
lolz
cak
dit
đjt
đkm
vcl
vkl
đm
đmm
đcm
clgt
lìn
điếm
nứng
chịch
đụ má
đụ mẹ
địt mẹ
địt má
con cặc
cái lồn
đồ đĩ
"""


def split_phrase(phrase: str) -> tuple[str, str, int, int]:
    word1, word2 = phrase.split(" ", 1)
    return word1, word2, len(word1) + len(word2), len(word1)


def vulgar_terms() -> set[str]:
    if not VULGAR_PATH.exists():
        VULGAR_PATH.write_text(DEFAULT_VULGAR.strip() + "\n", encoding="utf-8")
    terms: set[str] = set()
    for line in VULGAR_PATH.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if line:
            terms.add(line)
    return terms


def is_vulgar(phrase: str) -> bool:
    phrase = phrase.strip().lower()
    terms = vulgar_terms()
    if phrase in terms:
        return True
    if any(word in terms for word in phrase.split()):
        return True
    return any(term in phrase for term in terms if " " in term)


def _row_tuple(phrase: str, source: str, pool: str) -> tuple:
    word1, word2, letter_len, space_index = split_phrase(phrase)
    return (phrase, word1, word2, source, letter_len, space_index, pool)


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    exists = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='phrases'"
    ).fetchone()
    if exists:
        _migrate(conn, exists["sql"] or "")
    conn.executescript(SCHEMA)
    return conn


def _migrate(conn: sqlite3.Connection, create_sql: str) -> None:
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(phrases)")}
    needs_rebuild = "pool" not in cols or "phrase TEXT NOT NULL UNIQUE" in create_sql or "phrase TEXT UNIQUE" in create_sql
    if not needs_rebuild:
        return
    if "pool" not in cols:
        conn.execute("ALTER TABLE phrases ADD COLUMN pool TEXT NOT NULL DEFAULT 'raw'")
        conn.commit()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS phrases_v2 (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          phrase TEXT NOT NULL,
          word1 TEXT NOT NULL,
          word2 TEXT NOT NULL,
          source TEXT NOT NULL DEFAULT '',
          letter_len INTEGER NOT NULL,
          space_index INTEGER NOT NULL,
          pool TEXT NOT NULL DEFAULT 'raw'
            CHECK (pool IN ('raw', 'play', 'rejected')),
          UNIQUE (phrase, pool)
        );
        INSERT OR IGNORE INTO phrases_v2
          (phrase, word1, word2, source, letter_len, space_index, pool)
        SELECT phrase, word1, word2, source, letter_len, space_index, COALESCE(pool, 'raw')
        FROM phrases;
        DROP TABLE phrases;
        ALTER TABLE phrases_v2 RENAME TO phrases;
        """
    )
    conn.commit()


def import_vdict(path: Path | None = None) -> dict:
    """Add VDict 2-word headwords to Raw; copy non-vulgar ones into Play."""
    src = Path(path) if path else ROOT / "run" / "vdict" / "words.txt"
    rejected = set(all_phrases("rejected"))
    raw_rows: list[tuple] = []
    play_rows: list[tuple] = []
    rejected_rows: list[tuple] = []
    seen: set[str] = set()
    skipped = {"not_two": 0, "invalid": 0, "vulgar": 0, "rejected": 0}
    for line in src.read_text(encoding="utf-8").splitlines():
        text = unicodedata.normalize("NFC", line).strip()
        if not text:
            continue
        if len(text.split()) != 2:
            skipped["not_two"] += 1
            continue
        phrase = normalize_phrase(text)
        if not phrase or phrase in seen:
            if not phrase:
                skipped["invalid"] += 1
            continue
        seen.add(phrase)
        raw_rows.append(_row_tuple(phrase, "vdict", "raw"))
        if is_vulgar(phrase):
            skipped["vulgar"] += 1
            rejected_rows.append(_row_tuple(phrase, "vdict", "rejected"))
            continue
        if phrase in rejected:
            skipped["rejected"] += 1
            continue
        play_rows.append(_row_tuple(phrase, "vdict", "play"))
    conn = connect()
    try:
        conn.executemany(
            """
            INSERT OR IGNORE INTO phrases
              (phrase, word1, word2, source, letter_len, space_index, pool)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            raw_rows + play_rows + rejected_rows,
        )
        conn.commit()
    finally:
        conn.close()
    save_vdict_words(seen)
    return {
        "file": str(src),
        "two_word": len(seen),
        "raw_candidates": len(raw_rows),
        "play_candidates": len(play_rows),
        "skipped": skipped,
        **counts(),
    }


def save_vdict_words(phrases: list[str] | set[str]) -> int:
    rows = [(unicodedata.normalize("NFC", p).strip().lower(),) for p in phrases if p]
    if not rows:
        return vdict_count()
    conn = connect()
    try:
        conn.executemany("INSERT OR IGNORE INTO vdict_words (phrase) VALUES (?)", rows)
        conn.commit()
        n = conn.execute("SELECT COUNT(*) FROM vdict_words").fetchone()[0]
    finally:
        conn.close()
    return int(n)


def vdict_count() -> int:
    conn = connect()
    n = conn.execute("SELECT COUNT(*) FROM vdict_words").fetchone()[0]
    conn.close()
    return int(n)


def vdict_phrases() -> set[str]:
    conn = connect()
    rows = conn.execute("SELECT phrase FROM vdict_words").fetchall()
    conn.close()
    return {str(row["phrase"]) for row in rows}


def has_vdict(phrase: str) -> bool:
    key = unicodedata.normalize("NFC", phrase or "").strip().lower()
    if not key:
        return False
    conn = connect()
    row = conn.execute("SELECT 1 FROM vdict_words WHERE phrase = ?", (key,)).fetchone()
    conn.close()
    return row is not None


def backfill_vdict(path: Path | None = None) -> int:
    if vdict_count() > 0:
        return vdict_count()
    src = Path(path) if path else ROOT / "run" / "vdict" / "words.txt"
    if not src.exists():
        return 0
    found: list[str] = []
    for line in src.read_text(encoding="utf-8").splitlines():
        phrase = normalize_phrase(unicodedata.normalize("NFC", line))
        if phrase:
            found.append(phrase)
    return save_vdict_words(found)


def import_raw(rows: list[tuple[str, str]]) -> dict:
    conn = connect()
    payload = [_row_tuple(phrase, source, "raw") for phrase, source in rows]
    conn.executemany(
        """
        INSERT OR IGNORE INTO phrases
          (phrase, word1, word2, source, letter_len, space_index, pool)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )
    conn.commit()
    conn.close()
    return counts()


def filter_vulgar() -> dict:
    conn = connect()
    phrases = [
        row["phrase"]
        for row in conn.execute("SELECT DISTINCT phrase FROM phrases")
    ]
    moved = 0
    for phrase in phrases:
        if not is_vulgar(phrase):
            continue
        src = conn.execute(
            "SELECT source, word1, word2, letter_len, space_index FROM phrases WHERE phrase = ? LIMIT 1",
            (phrase,),
        ).fetchone()
        conn.execute(
            """
            INSERT OR IGNORE INTO phrases
              (phrase, word1, word2, source, letter_len, space_index, pool)
            VALUES (?, ?, ?, ?, ?, ?, 'rejected')
            """,
            (phrase, src["word1"], src["word2"], src["source"], src["letter_len"], src["space_index"]),
        )
        conn.execute("DELETE FROM phrases WHERE phrase = ? AND pool = 'play'", (phrase,))
        moved += 1
    conn.commit()
    conn.close()
    return {"rejected": moved, **counts()}


def seed_play_if_empty() -> dict:
    conn = connect()
    play_n = conn.execute("SELECT COUNT(*) FROM phrases WHERE pool = 'play'").fetchone()[0]
    conn.close()
    if play_n == 0:
        return curate_play()
    return {"seeded_play": 0, **counts()}


def _wordlist_dir() -> Path | None:
    for path in WORDLIST_DIRS:
        if (path / "Viet11K.txt").exists():
            return path
    return None


def quality_play_phrases() -> list[tuple[str, str]]:
    """Common 2-word compounds from Viet11K (not the full 59k dump)."""
    folder = _wordlist_dir()
    if not folder:
        return []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in (folder / "Viet11K.txt").read_text(encoding="utf-8").splitlines():
        text = unicodedata.normalize("NFC", line).strip().lower()
        parts = text.split()
        if len(parts) != 2:
            continue
        if not all(
            VIET_WORD_RE.fullmatch(part) and PLAY_MIN_WORD_LEN <= len(part) <= PLAY_MAX_WORD_LEN
            for part in parts
        ):
            continue
        phrase = f"{parts[0]} {parts[1]}"
        if phrase in seen or is_vulgar(phrase):
            continue
        seen.add(phrase)
        out.append((phrase, "Viet11K"))
    return out


def curate_play() -> dict:
    """Rebuild Play from common compounds; keep manual entries; leave Raw intact."""
    quality = quality_play_phrases()
    conn = connect()
    rejected = {
        row["phrase"]
        for row in conn.execute("SELECT phrase FROM phrases WHERE pool = 'rejected'")
    }
    if not quality:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO phrases
              (phrase, word1, word2, source, letter_len, space_index, pool)
            SELECT phrase, word1, word2, source, letter_len, space_index, 'play'
            FROM phrases
            WHERE pool = 'raw'
              AND length(word1) BETWEEN ? AND ?
              AND length(word2) BETWEEN ? AND ?
              AND phrase NOT IN (SELECT phrase FROM phrases WHERE pool = 'rejected')
            """,
            (PLAY_MIN_WORD_LEN, PLAY_MAX_WORD_LEN, PLAY_MIN_WORD_LEN, PLAY_MAX_WORD_LEN),
        )
        seeded = cur.rowcount
        conn.commit()
        conn.close()
        return {"seeded_play": seeded, "quality": 0, **counts()}

    conn.execute(
        "DELETE FROM phrases WHERE pool = 'play' AND source != 'manual'"
    )
    payload = [
        _row_tuple(phrase, source, "play")
        for phrase, source in quality
        if phrase not in rejected
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO phrases
          (phrase, word1, word2, source, letter_len, space_index, pool)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )
    for phrase, source in quality:
        if phrase in rejected:
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO phrases
              (phrase, word1, word2, source, letter_len, space_index, pool)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            _row_tuple(phrase, source, "raw"),
        )
    conn.commit()
    stats = counts()
    conn.close()
    return {"curated": True, "quality": len(payload), **stats}


def add_phrases(phrases: list[str], pool: str = "play", source: str = "import") -> dict:
    if pool not in POOLS:
        raise ValueError(f"pool must be one of {POOLS}")
    added: list[str] = []
    existed: list[str] = []
    conn = connect()
    try:
        for phrase in phrases:
            try:
                conn.execute(
                    """
                    INSERT INTO phrases (phrase, word1, word2, source, letter_len, space_index, pool)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    _row_tuple(phrase, source, pool),
                )
                if pool == "play":
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO phrases
                          (phrase, word1, word2, source, letter_len, space_index, pool)
                        VALUES (?, ?, ?, ?, ?, ?, 'raw')
                        """,
                        _row_tuple(phrase, source, "raw"),
                    )
                added.append(phrase)
            except sqlite3.IntegrityError:
                existed.append(phrase)
        conn.commit()
    finally:
        conn.close()
    return {"added": added, "existed": existed, "counts": counts()}


def set_pools(phrases: list[str], pool: str) -> dict:
    moved: list[str] = []
    missing: list[str] = []
    for phrase in phrases:
        if set_pool(phrase, pool):
            moved.append(phrase)
        else:
            missing.append(phrase)
    return {"moved": moved, "missing": missing, "counts": counts()}


def remove_phrases(phrases: list[str], pool: str | None = None) -> dict:
    removed: list[str] = []
    for phrase in phrases:
        if remove_phrase(phrase, pool):
            removed.append(phrase)
    return {"removed": removed, "counts": counts()}


def discard_phrases(phrases: list[str], pool: str | None = None) -> dict:
    """Play/Raw → Đã loại (lấy lại được). Rejected → xóa hẳn."""
    if pool == "rejected":
        result = remove_phrases(phrases, "rejected")
        return {
            "soft": False,
            "discarded": [],
            "removed": result["removed"],
            "counts": result["counts"],
        }
    moved = set_pools(phrases, "rejected")
    if pool == "raw":
        remove_phrases(moved["moved"], "raw")
    return {
        "soft": True,
        "discarded": moved["moved"],
        "removed": [],
        "counts": counts(),
    }


def add_phrase(phrase: str, source: str = "manual", pool: str = "play") -> bool:
    if pool not in POOLS:
        raise ValueError(f"pool must be one of {POOLS}")
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO phrases (phrase, word1, word2, source, letter_len, space_index, pool)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            _row_tuple(phrase, source, pool),
        )
        if pool == "play":
            conn.execute(
                """
                INSERT OR IGNORE INTO phrases
                  (phrase, word1, word2, source, letter_len, space_index, pool)
                VALUES (?, ?, ?, ?, ?, ?, 'raw')
                """,
                _row_tuple(phrase, source, "raw"),
            )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def set_pool(phrase: str, pool: str) -> bool:
    """Copy/move phrase into target pool without deleting raw dump."""
    if pool not in POOLS:
        raise ValueError(f"pool must be one of {POOLS}")
    conn = connect()
    src = conn.execute(
        "SELECT * FROM phrases WHERE phrase = ? LIMIT 1", (phrase,)
    ).fetchone()
    if not src:
        conn.close()
        return False
    conn.execute(
        """
        INSERT OR IGNORE INTO phrases
          (phrase, word1, word2, source, letter_len, space_index, pool)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (src["phrase"], src["word1"], src["word2"], src["source"], src["letter_len"], src["space_index"], pool),
    )
    if pool == "rejected":
        conn.execute("DELETE FROM phrases WHERE phrase = ? AND pool = 'play'", (phrase,))
    if pool == "raw":
        conn.execute("DELETE FROM phrases WHERE phrase = ? AND pool = 'play'", (phrase,))
    if pool == "play":
        conn.execute("DELETE FROM phrases WHERE phrase = ? AND pool = 'rejected'", (phrase,))
    conn.commit()
    conn.close()
    return True


def remove_phrase(phrase: str, pool: str | None = None) -> bool:
    conn = connect()
    if pool:
        cur = conn.execute("DELETE FROM phrases WHERE phrase = ? AND pool = ?", (phrase, pool))
    else:
        cur = conn.execute("DELETE FROM phrases WHERE phrase = ?", (phrase,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def all_phrases(pool: str = "play") -> list[str]:
    conn = connect()
    rows = conn.execute(
        "SELECT phrase FROM phrases WHERE pool = ? ORDER BY phrase", (pool,)
    ).fetchall()
    conn.close()
    return [row["phrase"] for row in rows]


def search(query: str, page: int = 1, limit: int = 50, pool: str = "play") -> dict:
    if pool not in POOLS:
        pool = "play"
    conn = connect()
    q = f"%{query.strip().lower()}%" if query.strip() else "%"
    total = conn.execute(
        "SELECT COUNT(*) FROM phrases WHERE pool = ? AND phrase LIKE ?",
        (pool, q),
    ).fetchone()[0]
    page = max(1, page)
    limit = min(200, max(1, limit))
    offset = (page - 1) * limit
    rows = conn.execute(
        """
        SELECT phrase, word1, word2, source, letter_len, space_index, pool
        FROM phrases
        WHERE pool = ? AND phrase LIKE ?
        ORDER BY phrase
        LIMIT ? OFFSET ?
        """,
        (pool, q, limit, offset),
    ).fetchall()
    conn.close()
    return {
        "pool": pool,
        "total": int(total),
        "page": page,
        "limit": limit,
        "pages": max(1, (int(total) + limit - 1) // limit),
        "items": [dict(row) for row in rows],
        "counts": counts(),
    }


def counts() -> dict[str, int]:
    conn = connect()
    out = {name: 0 for name in POOLS}
    for row in conn.execute("SELECT pool, COUNT(*) AS n FROM phrases GROUP BY pool"):
        out[row["pool"]] = int(row["n"])
    out["all"] = sum(out[name] for name in POOLS)
    conn.close()
    return out


def count(pool: str | None = None) -> int:
    stats = counts()
    if pool:
        return int(stats.get(pool, 0))
    return int(stats["all"])


def export_artifacts() -> dict:
    play = all_phrases("play")
    raw = all_phrases("raw")
    backfill_vdict()
    vdict = {p: 1 for p in sorted(vdict_phrases())}
    PLAY_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DATA_DIR / "phrases_two_words.json"
    js_path = PLAY_DIR / "phrases.js"
    json_path.write_text(json.dumps(play, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    js_path.write_text(
        "window.DOANCHU_PHRASES = "
        + json.dumps(play, ensure_ascii=False)
        + ";\nwindow.DOANCHU_VDICT = "
        + json.dumps(vdict, ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )
    return {
        "sqlite": str(DB_PATH),
        "play": len(play),
        "raw": len(raw),
        "rejected": count("rejected"),
        "vdict": len(vdict),
        "json": str(json_path),
        "js": str(js_path),
    }
