"""Persistence model for worker heartbeats."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from tasko_core.infrastructure.database.base import Base, utcnow
from tasko_core.infrastructure.database.query import ListSpec


class WorkerRecord(Base):
    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    queues: Mapped[list] = mapped_column(JSON, default=list)
    active_tasks: Mapped[int] = mapped_column(Integer, default=0)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True
    )


#: What the ``GET /api/workers`` list endpoint allows. Declared next to the
#: model, same pattern as ``TASK_LIST_SPEC``. Liveness (the TTL cutoff) is
#: applied by the service via ``run_list_query``'s ``extra_where`` — it's not
#: a user-facing filter, so it isn't listed here.
WORKER_LIST_SPEC = ListSpec(
    model=WorkerRecord,
    sortable_fields=frozenset({"id", "active_tasks", "first_seen_at", "last_heartbeat_at"}),
    filterable_fields=frozenset({"id"}),
    searchable_fields=("id",),
    default_sort=("id", "asc"),
)
