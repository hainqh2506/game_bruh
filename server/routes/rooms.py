from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from game.room import HUB
from server.httputil import json_error, read_json

router = APIRouter()


@router.post("/api/rooms")
async def api_rooms_create(request: Request) -> Any:
    body = await read_json(request)
    try:
        return HUB.create(str(body.get("name") or ""), body.get("settings"))
    except Exception as exc:
        return json_error(str(exc))


@router.post("/api/rooms/{room_id}/join")
async def api_rooms_join(room_id: str, request: Request) -> Any:
    body = await read_json(request)
    try:
        return HUB.join(room_id, str(body.get("name") or ""), body.get("token"))
    except KeyError as exc:
        return json_error(str(exc), 404)
    except PermissionError as exc:
        return json_error(str(exc), 403)
    except ValueError as exc:
        return json_error(str(exc))


@router.get("/api/rooms/{room_id}")
def api_rooms_get(room_id: str, token: str = "") -> Any:
    try:
        room, player = HUB.player_for(room_id, token)
    except KeyError as exc:
        return json_error(str(exc), 404)
    except PermissionError as exc:
        return json_error(str(exc), 403)
    return room.public(player)
