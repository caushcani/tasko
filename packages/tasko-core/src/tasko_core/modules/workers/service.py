"""Business logic for the workers module — heartbeat ingestion and liveness."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from tasko_core.infrastructure.database import run_list_query
from tasko_core.infrastructure.database.base import utcnow
from tasko_core.modules.common.pagination import ListParams
from tasko_core.modules.workers.models import WORKER_LIST_SPEC, WorkerRecord
from tasko_core.modules.workers.schemas import WorkerHeartbeat


async def record_heartbeat(session: AsyncSession, hb: WorkerHeartbeat) -> WorkerRecord:
    record = await session.get(WorkerRecord, hb.worker_id)
    now = utcnow()
    if record is None:
        record = WorkerRecord(id=hb.worker_id, first_seen_at=now)
        session.add(record)
    record.queues = hb.queues
    record.active_tasks = hb.active_tasks
    record.last_heartbeat_at = now
    await session.flush()
    return record


async def list_workers(
    session: AsyncSession,
    params: ListParams,
    *,
    ttl_seconds: int,
    worker_id: str | None = None,
) -> tuple[list[WorkerRecord], int]:
    """Filtered / sorted / searched / paginated page of live workers.

    "Live" means heartbeated within ``ttl_seconds`` — a service-level cutoff,
    not a user-facing filter, so it's threaded through as ``extra_where``
    rather than exposed on ``WORKER_LIST_SPEC``.
    """
    cutoff = utcnow() - timedelta(seconds=ttl_seconds)
    filters = {k: v for k, v in {"id": worker_id}.items() if v is not None}
    return await run_list_query(
        session,
        WORKER_LIST_SPEC,
        offset=params.offset,
        limit=params.limit,
        sort_columns=params.sort_columns,
        sort_orders=params.sort_orders,
        search=params.search,
        filters=filters,
        extra_where=[WorkerRecord.last_heartbeat_at >= cutoff],
    )


async def get_worker(session: AsyncSession, worker_id: str) -> WorkerRecord | None:
    """A single worker by id, regardless of liveness — useful for postmortem
    ("this worker died 2h ago, here's its last known state")."""
    return await session.get(WorkerRecord, worker_id)
