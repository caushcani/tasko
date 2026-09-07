"""Aggregate queries behind the Overview page.

Deliberately simple: a few ``COUNT`` / ``AVG`` queries for the headline metrics,
and one row-scan for the throughput sparkline (bucketed in Python so it works
the same on SQLite and Postgres — the window is bounded and this is one request
per page load at self-hosted scale).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tasko_core.modules.stats.schemas import (
    Metric,
    OverviewOut,
    ThroughputBucket,
    ThroughputOut,
)
from tasko_core.modules.tasks.enums import TaskState
from tasko_core.modules.tasks.models import TaskRecord
from tasko_core.modules.workers.models import WorkerRecord

_TERMINAL = (TaskState.SUCCESS, TaskState.FAILURE)

#: window name -> total seconds; every window is drawn as 24 buckets
WINDOWS: dict[str, int] = {
    "1h": 3600,
    "24h": 86_400,
    "7d": 604_800,
}
_BUCKETS = 24
#: guard against an unbounded scan on a very busy fleet
_SCAN_LIMIT = 100_000


async def _window_counts(
    session: AsyncSession, start: datetime, end: datetime
) -> tuple[int, int, float | None]:
    """(successes, failures, avg_execution_ms) for tasks finished in [start, end)."""
    success_one = case((TaskRecord.state == TaskState.SUCCESS, 1), else_=0)
    failure_one = case((TaskRecord.state == TaskState.FAILURE, 1), else_=0)
    row = (
        await session.execute(
            select(
                func.coalesce(func.sum(success_one), 0),
                func.coalesce(func.sum(failure_one), 0),
                func.avg(TaskRecord.execution_ms),
            ).where(
                TaskRecord.finished_at >= start,
                TaskRecord.finished_at < end,
                TaskRecord.state.in_(_TERMINAL),
            )
        )
    ).one()
    successes, failures, avg_ms = row
    return int(successes or 0), int(failures or 0), (float(avg_ms) if avg_ms is not None else None)


async def overview(session: AsyncSession, *, ttl_seconds: int) -> OverviewOut:
    now = datetime.now(UTC)
    day = timedelta(days=1)

    cur_s, cur_f, cur_avg = await _window_counts(session, now - day, now)
    prev_s, prev_f, prev_avg = await _window_counts(session, now - 2 * day, now - day)

    def rate(s: int, f: int) -> float:
        total = s + f
        return s / total if total else 0.0

    workers_online = (
        await session.scalar(
            select(func.count())
            .select_from(WorkerRecord)
            .where(WorkerRecord.last_heartbeat_at >= now - timedelta(seconds=ttl_seconds))
        )
    ) or 0
    workers_known = await session.scalar(select(func.count()).select_from(WorkerRecord)) or 0

    return OverviewOut(
        tasks_processed=Metric(value=cur_s + cur_f, previous=prev_s + prev_f),
        success_rate=Metric(value=rate(cur_s, cur_f), previous=rate(prev_s, prev_f)),
        avg_duration_ms=Metric(value=cur_avg or 0.0, previous=prev_avg or 0.0),
        workers_online=int(workers_online),
        workers_known=int(workers_known),
    )


async def throughput(session: AsyncSession, window: str) -> ThroughputOut:
    total_seconds = WINDOWS[window]
    bucket_seconds = total_seconds // _BUCKETS
    now = datetime.now(UTC)
    start = now - timedelta(seconds=total_seconds)

    rows = (
        await session.execute(
            select(TaskRecord.finished_at, TaskRecord.state)
            .where(
                TaskRecord.finished_at >= start,
                TaskRecord.state.in_(_TERMINAL),
            )
            .limit(_SCAN_LIMIT)
        )
    ).all()

    completed = [0] * _BUCKETS
    failed = [0] * _BUCKETS
    for finished_at, state in rows:
        if finished_at is None:
            continue
        if finished_at.tzinfo is None:
            finished_at = finished_at.replace(tzinfo=UTC)
        idx = int((finished_at - start).total_seconds() // bucket_seconds)
        if idx < 0 or idx >= _BUCKETS:
            continue
        if state == TaskState.SUCCESS:
            completed[idx] += 1
        else:
            failed[idx] += 1

    buckets = [
        ThroughputBucket(
            start=start + timedelta(seconds=bucket_seconds * i),
            completed=completed[i],
            failed=failed[i],
        )
        for i in range(_BUCKETS)
    ]
    return ThroughputOut(
        window=window,
        bucket_seconds=bucket_seconds,
        buckets=buckets,
        total_completed=sum(completed),
        total_failed=sum(failed),
    )
