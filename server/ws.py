"""Room WebSocket endpoint. Register a Client.* handler to add a command."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import parse_qs

from fastapi import WebSocket, WebSocketDisconnect

from game.protocol import Client, Server
from game.room import ALLOWED_REACTIONS, HUB, Player, RoomSession
from game.ws import BUS

Handler = Callable[[WebSocket, RoomSession, Player, dict[str, Any]], Awaitable[None]]


async def on_ping(ws: WebSocket, room: RoomSession, player: Player, message: dict[str, Any]) -> None:
    await BUS.send(ws, {"type": Server.PONG})


async def on_start(ws: WebSocket, room: RoomSession, player: Player, message: dict[str, Any]) -> None:
    await BUS.broadcast(room.id, room.start(player))


async def on_rematch(ws: WebSocket, room: RoomSession, player: Player, message: dict[str, Any]) -> None:
    await BUS.broadcast(room.id, room.rematch(player))


async def on_guess(ws: WebSocket, room: RoomSession, player: Player, message: dict[str, Any]) -> None:
    out = room.submit_guess(player, str(message.get("guess") or ""))
    await BUS.send(ws, out["to_player"])
    await BUS.broadcast(room.id, out["broadcast"])
    if out.get("round_finished"):
        await BUS.broadcast(room.id, out["round_finished"])
    if out.get("finished"):
        await BUS.broadcast(room.id, out["finished"])


async def on_next_round(ws: WebSocket, room: RoomSession, player: Player, message: dict[str, Any]) -> None:
    started_event = room.next_round(player)
    await BUS.broadcast(room.id, started_event)


async def on_reaction(ws: WebSocket, room: RoomSession, player: Player, message: dict[str, Any]) -> None:
    emoji = str(message.get("emoji") or "").strip()
    if emoji not in ALLOWED_REACTIONS:
        return
    now = time.time()
    if now - player.last_reaction_at < 0.3:
        return
    player.last_reaction_at = now
    await BUS.broadcast(
        room.id,
        {
            "type": Server.REACTION,
            "player_id": player.id,
            "name": player.name,
            "emoji": emoji,
        },
    )


HANDLERS: dict[str, Handler] = {
    Client.PING: on_ping,
    Client.START: on_start,
    Client.REMATCH: on_rematch,
    Client.GUESS: on_guess,
    Client.NEXT_ROUND: on_next_round,
    Client.REACTION: on_reaction,
}


async def room_socket(websocket: WebSocket) -> None:
    qs = parse_qs(websocket.scope.get("query_string", b"").decode())
    room_id = (qs.get("room") or [""])[0]
    token = (qs.get("token") or [""])[0]
    try:
        room, _player = HUB.player_for(room_id, token)
    except (KeyError, PermissionError):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    await BUS.register(room.id, websocket)
    await BUS.send(websocket, room.public(_player))
    await BUS.broadcast(
        room.id,
        {"type": Server.PEER_UPDATE, "players": room.roster()},
        exclude=websocket,
    )
    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=30)
            except asyncio.TimeoutError:
                await BUS.send(websocket, {"type": Server.PING})
                continue
            kind = str(message.get("type") or "")
            try:
                room, player = HUB.player_for(room_id, token)
                handler = HANDLERS.get(kind)
                if handler is None:
                    await BUS.send(
                        websocket,
                        {"type": Server.ERROR, "message": "Lệnh không hỗ trợ"},
                    )
                    continue
                await handler(websocket, room, player, message)
            except (ValueError, PermissionError, KeyError) as exc:
                await BUS.send(websocket, {"type": Server.ERROR, "message": str(exc)})
    except WebSocketDisconnect:
        pass
    finally:
        await BUS.unregister(room.id, websocket)
        peer = HUB.mark_disconnected(room.id, token)
        if peer:
            await BUS.broadcast(room.id, peer)
