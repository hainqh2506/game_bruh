from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/api/reload", response_model=None)
async def api_reload(request: Request, gen: int = 0):
    if not request.app.state.reload:
        return JSONResponse({"error": "off"}, status_code=404)
    state = request.app.state.reload_state
    loop = asyncio.get_running_loop()
    generation = await loop.run_in_executor(None, state.wait_after, gen)
    return {"generation": generation}
