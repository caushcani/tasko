"""Persistence model for schedules synced from a Taskiq ``ScheduleSource``.

Definitions only — when a schedule *fires*, the scheduler stamps a
``schedule_id`` label onto the kicked task, which ``tasko-middleware`` forwards
on the normal task event. So "last run" / "recent runs" for a schedule are
derived from :class:`~tasko_core.modules.tasks.models.TaskRecord`, not stored
here.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from tasko_core.infrastructure.database.base import Base, utcnow
from tasko_core.infrastructure.database.query import ListSpec


class ScheduleRecord(Base):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)  # taskiq schedule_id
    task_name: Mapped[str] = mapped_column(String(255), index=True)
    #: which ScheduleSource reported it (its class name) — a fleet may run
    #: several (label-based, database-backed, ...).
    source: Mapped[str] = mapped_column(String(128), default="", index=True)

    # Exactly one of these three shapes is set, mirroring taskiq's ScheduledTask.
    cron: Mapped[str | None] = mapped_column(String(128), default=None)
    cron_offset: Mapped[str | None] = mapped_column(String(64), default=None)
    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    interval_seconds: Mapped[int | None] = mapped_column(Integer, default=None)

    args: Mapped[list] = mapped_column(JSON, default=list)
    kwargs: Mapped[dict] = mapped_column(JSON, default=dict)
    labels: Mapped[dict] = mapped_column(JSON, default=dict)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    #: bumped every sync a source still reports this schedule; a stale value
    #: means the schedule was removed from its source (kept for run history).
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True
    )


#: What ``GET /api/schedules`` allows. ``last_fired_at`` / ``next_fire_at`` are
#: computed in the response (from TaskRecord and from the cron expression), not
#: columns — so they're not sortable here.
SCHEDULE_LIST_SPEC = ListSpec(
    model=ScheduleRecord,
    sortable_fields=frozenset({"id", "task_name", "source", "first_seen_at", "last_seen_at"}),
    filterable_fields=frozenset({"task_name", "source"}),
    searchable_fields=("id", "task_name"),
    default_sort=("task_name", "asc"),
)
