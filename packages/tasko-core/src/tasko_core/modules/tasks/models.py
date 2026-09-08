"""Persistence model for ingested task lifecycle events."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tasko_core.infrastructure.database.base import Base, utcnow
from tasko_core.infrastructure.database.query import ListSpec, RelationSpec
from tasko_core.modules.tasks.enums import TaskState
from tasko_core.modules.workers.models import WorkerRecord


class TaskRecord(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # taskiq task_id
    name: Mapped[str] = mapped_column(String(255), index=True)
    queue: Mapped[str] = mapped_column(String(128), index=True)
    state: Mapped[TaskState] = mapped_column(Enum(TaskState), index=True)
    worker_id: Mapped[str | None] = mapped_column(String(128), index=True)
    #: set when this run was kicked by the scheduler — the scheduler stamps a
    #: `schedule_id` label on the task and tasko-middleware forwards it.
    schedule_id: Mapped[str | None] = mapped_column(String(128), index=True)
    #: the task that was running when this one was `.kiq()`'d — captured by
    #: tasko-middleware's `pre_send` hook via a contextvar. Constraint-free
    #: (the parent may predate the middleware, or its event may arrive later).
    parent_task_id: Mapped[str | None] = mapped_column(String(64), index=True)

    args: Mapped[list] = mapped_column(JSON, default=list)
    kwargs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict | None] = mapped_column(JSON, default=None)
    traceback: Mapped[str | None] = mapped_column(Text, default=None)

    retries: Mapped[int] = mapped_column(Integer, default=0)
    execution_ms: Mapped[int | None] = mapped_column(Integer, default=None)

    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # worker_id is a plain string (a worker may never send a heartbeat), so this
    # is a constraint-free, read-only relationship — enough to join/sort/filter
    # on worker columns, never blocks task ingest.
    worker: Mapped[WorkerRecord | None] = relationship(
        WorkerRecord,
        primaryjoin="foreign(TaskRecord.worker_id) == WorkerRecord.id",
        viewonly=True,
        lazy="noload",
    )

    __table_args__ = (Index("ix_tasks_queue_state", "queue", "state"),)


#: What the ``GET /api/tasks`` list endpoint allows. Declared next to the model.
TASK_LIST_SPEC = ListSpec(
    model=TaskRecord,
    sortable_fields=frozenset(
        {
            "id",
            "name",
            "queue",
            "state",
            "execution_ms",
            "retries",
            "queued_at",
            "started_at",
            "finished_at",
            "updated_at",
        }
    ),
    filterable_fields=frozenset(
        {"name", "queue", "state", "worker_id", "schedule_id", "parent_task_id"}
    ),
    searchable_fields=("id", "name", "traceback"),
    default_sort=("updated_at", "desc"),
    relations={
        "worker": RelationSpec(
            attr="worker",
            model=WorkerRecord,
            sortable_fields=frozenset({"last_heartbeat_at", "active_tasks"}),
            filterable_fields=frozenset({"id"}),
        ),
    },
)
