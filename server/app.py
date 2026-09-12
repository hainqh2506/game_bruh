"""Compose FastAPI app from route modules + WebSocket."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from game.room import HUB
from game.ws import BUS
from paths import PUBLIC_DIR
from server.httputil import NoCacheStatic
from server.routes import config, phrases, reload as reload_routes, rooms
from server.ws import room_socket


def create_app(*, reload: bool, debug: bool, reload_state: Any) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        async def loop() -> None:
            while True:
                await asyncio.sleep(10)
                for room_id, event in HUB.sweep_stale():
                    await BUS.broadcast(room_id, event)

        task = asyncio.create_task(loop())
        try:
            yield
        finally:
            task.cancel()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.reload = reload
    app.state.debug = debug
    app.state.reload_state = reload_state
    app.add_middleware(NoCacheStatic)

    for module in (config, reload_routes, phrases, rooms):
        app.include_router(module.router)

    app.add_api_websocket_route("/ws", room_socket)

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(PUBLIC_DIR / "index.html")

    app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="static")
    return app
