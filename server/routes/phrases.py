from __future__ import annotations

from typing import Any

import db
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from game.phrases import normalize_phrase
from server.httputil import json_error, read_json

router = APIRouter()


def _require_debug(request: Request):
    if request.app.state.debug:
        return None
    return json_error("debug disabled", 403)


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


@router.post("/api/phrases")
async def api_phrases_post(request: Request) -> Any:
    blocked = _require_debug(request)
    if blocked:
        return blocked
    body = await read_json(request)
    phrase = normalize_phrase(str(body.get("phrase") or ""))
    pool = str(body.get("pool") or "play")
    if not phrase:
        return json_error("Cần cụm đúng 2 từ tiếng Việt")
    created = db.add_phrase(phrase, source="manual", pool=pool)
    db.export_artifacts()
    return {"ok": True, "created": created, "phrase": phrase, "counts": db.counts()}


@router.patch("/api/phrases")
async def api_phrases_patch(request: Request) -> Any:
    blocked = _require_debug(request)
    if blocked:
        return blocked
    body = await read_json(request)
    phrase = normalize_phrase(str(body.get("phrase") or "")) or str(body.get("phrase") or "").strip().lower()
    pool = str(body.get("pool") or "")
    if not phrase or pool not in db.POOLS:
        return json_error("phrase/pool không hợp lệ")
    ok = db.set_pool(phrase, pool)
    db.export_artifacts()
    return JSONResponse(
        {"ok": ok, "phrase": phrase, "pool": pool, "counts": db.counts()},
        status_code=200 if ok else 404,
    )


@router.delete("/api/phrases")
async def api_phrases_delete(request: Request) -> Any:
    blocked = _require_debug(request)
    if blocked:
        return blocked
    body = await read_json(request)
    phrase = normalize_phrase(str(body.get("phrase") or "")) or str(body.get("phrase") or "").strip().lower()
    pool = body.get("pool")
    ok = db.remove_phrase(phrase, pool if pool in db.POOLS else None)
    db.export_artifacts()
    return JSONResponse({"ok": ok, "counts": db.counts()}, status_code=200 if ok else 404)
