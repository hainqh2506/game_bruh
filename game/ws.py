"""In-memory fan-out. Transport-agnostic (any object with send_json)."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol


class JsonSocket(Protocol):
    async def send_json(self, data: Any) -> None: ...


class Broadcaster:
    def __init__(self) -> None:
        self._rooms: dict[str, set[JsonSocket]] = {}
        self._lock = asyncio.Lock()

    async def register(self, room_id: str, ws: JsonSocket) -> None:
        async with self._lock:
            self._rooms.setdefault(room_id.upper(), set()).add(ws)

    async def unregister(self, room_id: str, ws: JsonSocket) -> None:
        async with self._lock:
            conns = self._rooms.get(room_id.upper())
            if not conns:
                return
            conns.discard(ws)
            if not conns:
                self._rooms.pop(room_id.upper(), None)

    async def send(self, ws: JsonSocket, payload: dict[str, Any]) -> None:
        try:
            await ws.send_json(payload)
        except Exception:
            return

    async def broadcast(
        self,
        room_id: str,
        payload: dict[str, Any],
        *,
        exclude: JsonSocket | None = None,
    ) -> None:
        async with self._lock:
            conns = list(self._rooms.get(room_id.upper(), ()))
        dead: list[JsonSocket] = []
        for ws in conns:
            if ws is exclude:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.unregister(room_id, ws)


BUS = Broadcaster()
