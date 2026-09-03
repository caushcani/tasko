"""The ``/ws`` live-update stream. Subscribes clients to the realtime hub."""

from __future__ import annotations

import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from tasko_core.infrastructure.realtime import hub

router = APIRouter()


@router.websocket("/ws")
async def stream(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        while True:
            # We don't expect client messages; this keeps the socket open and
            # surfaces disconnects promptly.
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        with contextlib.suppress(Exception):
            await hub.disconnect(ws)
