"""Queue depth — served from the active broker adapter."""

from __future__ import annotations

from fastapi import APIRouter

from tasko_core.infrastructure.broker import AdapterDep
from tasko_core.modules.queues.schemas import QueueOut

router = APIRouter(tags=["queues"])


@router.get("/queues", response_model=list[QueueOut])
async def list_queues(adapter: AdapterDep) -> list[QueueOut]:
    return [QueueOut.from_stats(q) for q in await adapter.list_queues()]
