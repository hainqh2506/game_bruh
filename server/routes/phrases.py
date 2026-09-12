from __future__ import annotations

from typing import Any

import db
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from game.phrases import normalize_phrase, parse_import_lines
from server.httputil import json_error, read_json

router = APIRouter()


def _require_debug(request: Request):
    if request.app.state.debug:
        return None
    return json_error("debug disabled", 403)


def _as_stored_phrase(item: str) -> str:
    text = str(item or "")
    return normalize_phrase(text) or text.strip().lower()


def _phrase_list(body: dict[str, Any], *, strict: bool = False) -> tuple[list[str], list[str]]:
    if body.get("text"):
        parsed = parse_import_lines(str(body.get("text") or ""))
        return parsed["valid"], parsed["invalid"]
    raw = body.get("phrases")
    items = raw if isinstance(raw, list) else [body.get("phrase")]
    valid: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()
    for item in items:
        stored = _as_stored_phrase(str(item or ""))
        if not stored:
            continue
        if strict and not normalize_phrase(stored):
            invalid.append(str(item).strip())
            continue
        if stored in seen:
            continue
        seen.add(stored)
        valid.append(stored)
    return valid, invalid


@router.get("/api/phrases")
def api_phrases_get(
    request: Request,
    q: str = "",
    pool: str = "play",
    page: int = 1,
    limit: int = 50,
) -> Any:
    blocked = _require_debug(request)
    if blocked:
        return blocked
    return db.search(q, page, limit, pool)


@router.get("/api/phrases/export")
def api_phrases_export(request: Request, pool: str = "play") -> Any:
    blocked = _require_debug(request)
    if blocked:
        return blocked
    if pool not in db.POOLS:
        return json_error("pool không hợp lệ")
    text = "\n".join(db.all_phrases(pool))
    if text:
        text += "\n"
    filename = f"doanchu-{pool}.txt"
    return PlainTextResponse(
        text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/phrases")
async def api_phrases_post(request: Request) -> Any:
    blocked = _require_debug(request)
    if blocked:
        return blocked
    body = await read_json(request)
    pool = str(body.get("pool") or "play")
    if pool not in db.POOLS:
        return json_error("pool không hợp lệ")
    valid, invalid = _phrase_list(body, strict=True)
    if not valid and not invalid:
        return json_error("Cần cụm đúng 2 từ tiếng Việt")
    source = "import" if body.get("text") or isinstance(body.get("phrases"), list) else "manual"
    result = db.add_phrases(valid, pool=pool, source=source)
    db.export_artifacts()
    return {
        "ok": True,
        "created": bool(result["added"]),
        "added": result["added"],
        "existed": result["existed"],
        "invalid": invalid,
        "counts": result["counts"],
    }


@router.patch("/api/phrases")
async def api_phrases_patch(request: Request) -> Any:
    blocked = _require_debug(request)
    if blocked:
        return blocked
    body = await read_json(request)
    pool = str(body.get("pool") or "")
    valid, _invalid = _phrase_list(body)
    if not valid or pool not in db.POOLS:
        return json_error("phrase/pool không hợp lệ")
    result = db.set_pools(valid, pool)
    db.export_artifacts()
    return JSONResponse(
        {
            "ok": bool(result["moved"]),
            "moved": result["moved"],
            "missing": result["missing"],
            "pool": pool,
            "counts": result["counts"],
        },
        status_code=200 if result["moved"] else 404,
    )


@router.delete("/api/phrases")
async def api_phrases_delete(request: Request) -> Any:
    blocked = _require_debug(request)
    if blocked:
        return blocked
    body = await read_json(request)
    pool = body.get("pool")
    valid, _invalid = _phrase_list(body)
    if not valid:
        return json_error("phrase không hợp lệ")
    result = db.discard_phrases(valid, pool if pool in db.POOLS else None)
    db.export_artifacts()
    ok = bool(result["discarded"] or result["removed"])
    return JSONResponse(
        {
            "ok": ok,
            "soft": result["soft"],
            "discarded": result["discarded"],
            "removed": result["removed"],
            "counts": result["counts"],
        },
        status_code=200 if ok else 404,
    )
