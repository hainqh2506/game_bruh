from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

import db
from game.room import HUB
from server.presence import SOLO

router = APIRouter()


@router.get("/api/config")
def api_config(request: Request) -> dict:
    debug = bool(request.app.state.debug)
    payload: dict[str, Any] = {
        "debug": debug,
        "rooms": True,
        "limits": {**HUB.usage(), **SOLO.usage()},
    }
    if debug:
        payload["counts"] = db.counts()
    return payload
