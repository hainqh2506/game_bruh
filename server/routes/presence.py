from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from server.httputil import json_error, read_json
from server.presence import SOLO

router = APIRouter()


@router.post("/api/presence")
async def api_presence(request: Request) -> Any:
    body = await read_json(request)
    try:
        return SOLO.touch(body.get("token") if isinstance(body.get("token"), str) else None)
    except ValueError as exc:
        return json_error(str(exc), 503)
