"""Worker fleet — heartbeat ingest, a paginated liveness list, and detail.

Liveness is middleware-reported (``POST /workers/heartbeat``); the list is
DB-only, run through the same list-query engine as tasks (filter/sort/search/
paginate). Brokers that natively track consumers can still implement
``BrokerAdapter.list_workers()`` (see docs/writing-a-broker-adapter.md), but
that's not merged in here — a live Python-side merge can't be paginated
alongside a SQL query. If a real adapter needs this later, the adapter should
sync into ``WorkerRecord`` (e.g. on startup / on an interval) so the DB stays
the single source of truth this endpoint queries.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from tasko_core.infrastructure.database import SessionDep
from tasko_core.modules.common.pagination import ListParamsDep, PaginatedResponse
from tasko_core.modules.workers import service
from tasko_core.modules.workers.schemas import WorkerHeartbeat, WorkerOut

router = APIRouter(tags=["workers"])


@router.post("/workers/heartbeat", status_code=202)
async def heartbeat(hb: WorkerHeartbeat, session: SessionDep) -> dict[str, str]:
    await service.record_heartbeat(session, hb)
    return {"status": "accepted"}


@router.get("/workers", response_model=PaginatedResponse[WorkerOut])
async def list_workers(
    params: ListParamsDep,
    session: SessionDep,
    request: Request,
    worker_id: str | None = None,
) -> PaginatedResponse[WorkerOut]:
    ttl = request.app.state.config.workers.ttl_seconds
    rows, total = await service.list_workers(session, params, ttl_seconds=ttl, worker_id=worker_id)
    return PaginatedResponse[WorkerOut](
        items=[WorkerOut.model_validate(r) for r in rows],
        total_count=total,
        offset=params.offset,
        limit=params.limit,
    )


@router.get("/workers/{worker_id}", response_model=WorkerOut)
async def get_worker(worker_id: str, session: SessionDep) -> WorkerOut:
    record = await service.get_worker(session, worker_id)
    if record is None:
        raise HTTPException(status_code=404, detail="worker not found")
    return WorkerOut.model_validate(record)
