"""Business logic for the workers module — heartbeat ingestion and liveness."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasko_core.infrastructure.database.base import utcnow
from tasko_core.modules.workers.models import WorkerRecord
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


async def list_live_workers(session: AsyncSession, ttl_seconds: int) -> list[WorkerRecord]:
    """Workers whose last heartbeat is within ``ttl_seconds``."""
    cutoff = utcnow() - timedelta(seconds=ttl_seconds)
    stmt = (
        select(WorkerRecord)
        .where(WorkerRecord.last_heartbeat_at >= cutoff)
        .order_by(WorkerRecord.id)
    )
    return list((await session.scalars(stmt)).all())
