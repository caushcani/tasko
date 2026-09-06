"""Business logic for the schedules module — sync, listing, and the two
derived fields (last fired / next fire)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tasko_core.infrastructure.database import run_list_query
from tasko_core.infrastructure.database.base import utcnow
from tasko_core.modules.common.pagination import ListParams
from tasko_core.modules.schedules.models import SCHEDULE_LIST_SPEC, ScheduleRecord
from tasko_core.modules.schedules.schemas import ScheduledTaskIn
from tasko_core.modules.tasks.models import TaskRecord


async def sync_schedules(
    session: AsyncSession, source: str, schedules: list[ScheduledTaskIn]
) -> tuple[int, int]:
    """Upsert every schedule a source currently reports; anything previously
    from that source but absent now is deleted. Returns ``(synced, removed)``.
    """
    now = utcnow()
    seen: set[str] = set()

    for item in schedules:
        seen.add(item.schedule_id)
        record = await session.get(ScheduleRecord, item.schedule_id)
        if record is None:
            record = ScheduleRecord(id=item.schedule_id, first_seen_at=now)
            session.add(record)
        record.task_name = item.task_name
        record.source = source
        record.cron = item.cron
        record.cron_offset = item.cron_offset
        record.scheduled_time = item.time
        record.interval_seconds = item.interval_seconds
        record.args = item.args
        record.kwargs = item.kwargs
        record.labels = item.labels
        record.last_seen_at = now

    existing = (
        await session.scalars(select(ScheduleRecord).where(ScheduleRecord.source == source))
    ).all()
    removed = 0
    for record in existing:
        if record.id not in seen:
            await session.delete(record)
            removed += 1

    await session.flush()
    return len(schedules), removed


async def list_schedules(
    session: AsyncSession,
    params: ListParams,
    *,
    task_name: str | None = None,
    source: str | None = None,
) -> tuple[list[ScheduleRecord], int]:
    filters = {k: v for k, v in {"task_name": task_name, "source": source}.items() if v is not None}
    return await run_list_query(
        session,
        SCHEDULE_LIST_SPEC,
        offset=params.offset,
        limit=params.limit,
        sort_columns=params.sort_columns,
        sort_orders=params.sort_orders,
        search=params.search,
        filters=filters,
    )


async def get_schedule(session: AsyncSession, schedule_id: str) -> ScheduleRecord | None:
    return await session.get(ScheduleRecord, schedule_id)


async def last_fired_map(
    session: AsyncSession, schedule_ids: list[str]
) -> dict[str, datetime]:
    """Most recent activity timestamp per schedule_id, read off TaskRecord."""
    if not schedule_ids:
        return {}
    stamp = func.coalesce(TaskRecord.started_at, TaskRecord.queued_at, TaskRecord.updated_at)
    rows = await session.execute(
        select(TaskRecord.schedule_id, func.max(stamp))
        .where(TaskRecord.schedule_id.in_(schedule_ids))
        .group_by(TaskRecord.schedule_id)
    )
    return {sid: ts for sid, ts in rows if sid is not None and ts is not None}


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes (no tz type); treat those as UTC so
    they compare cleanly against ``utcnow()``."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def next_fire_at(
    record: ScheduleRecord, *, after: datetime, last_fired: datetime | None
) -> datetime | None:
    """Best-effort next run time.

    * cron — the next match after ``after`` (``cron_offset`` is not applied; a
      dashboard estimate, not the scheduler's own clock).
    * interval — ``last_fired + interval`` if that's still ahead, else
      ``after + interval``.
    * one-off ``time`` — that instant, or ``None`` once it's passed.
    """
    if record.cron:
        try:
            from croniter import croniter
        except ImportError:  # pragma: no cover - croniter is a hard dep
            return None
        try:
            return croniter(record.cron, after).get_next(datetime)
        except (ValueError, KeyError):
            return None
    if record.interval_seconds:
        step = timedelta(seconds=record.interval_seconds)
        base = _aware(last_fired) or _aware(record.first_seen_at) or after
        nxt = base + step
        while nxt <= after:
            nxt += step
        return nxt
    if record.scheduled_time:
        when = _aware(record.scheduled_time)
        return when if when and when > after else None
    return None
