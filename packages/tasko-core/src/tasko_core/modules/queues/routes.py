"""Queue depth — served live from the active broker adapter.

There's no ``queues`` table: this is a read straight off the broker (for
Redis, a ``SCAN`` over the list keys), and queue cardinality is low, so it's
a plain unpaginated list rather than going through the list-query engine.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tasko_core.infrastructure.broker import AdapterDep
from tasko_core.modules.queues.schemas import QueueOut

router = APIRouter(tags=["queues"])


@router.get("/queues", response_model=list[QueueOut])
async def list_queues(adapter: AdapterDep) -> list[QueueOut]:
    return [QueueOut.from_stats(q) for q in await adapter.list_queues()]


@router.get("/queues/{queue_name}", response_model=QueueOut)
async def get_queue(queue_name: str, adapter: AdapterDep) -> QueueOut:
    stats = await adapter.get_queue(queue_name)
    if stats is None:
        raise HTTPException(status_code=404, detail="queue not found")
    return QueueOut.from_stats(stats)
