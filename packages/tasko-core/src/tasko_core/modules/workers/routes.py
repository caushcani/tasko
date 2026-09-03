"""Worker fleet — heartbeat ingest + a liveness list.

Liveness is middleware-reported (``POST /workers/heartbeat``). Brokers that
natively track consumers also contribute through the active adapter, and the
two are merged here by id (heartbeat data wins).
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from tasko_core.infrastructure.broker import AdapterDep
from tasko_core.infrastructure.database import SessionDep
from tasko_core.modules.workers import service
from tasko_core.modules.workers.schemas import WorkerHeartbeat, WorkerOut

router = APIRouter(tags=["workers"])


@router.post("/workers/heartbeat", status_code=202)
async def heartbeat(hb: WorkerHeartbeat, session: SessionDep) -> dict[str, str]:
    await service.record_heartbeat(session, hb)
    return {"status": "accepted"}


@router.get("/workers", response_model=list[WorkerOut])
async def list_workers(
    request: Request, session: SessionDep, adapter: AdapterDep
) -> list[WorkerOut]:
    ttl = request.app.state.config.workers.ttl_seconds
    by_id: dict[str, WorkerOut] = {}

    for info in await adapter.list_workers():
        by_id[info.id] = WorkerOut(
            id=info.id,
            queues=info.queues,
            active_tasks=info.active_tasks,
            first_seen_at=info.last_heartbeat_at,
            last_heartbeat_at=info.last_heartbeat_at,
        )

    for record in await service.list_live_workers(session, ttl):
        by_id[record.id] = WorkerOut.model_validate(record)

    return [by_id[k] for k in sorted(by_id)]
