"""Persistence model for ingested task lifecycle events."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tasko_core.infrastructure.database.base import Base, utcnow
from tasko_core.modules.tasks.enums import TaskState


class TaskRecord(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # taskiq task_id
    name: Mapped[str] = mapped_column(String(255), index=True)
    queue: Mapped[str] = mapped_column(String(128), index=True)
    state: Mapped[TaskState] = mapped_column(Enum(TaskState), index=True)
    worker_id: Mapped[str | None] = mapped_column(String(128), index=True)

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

    __table_args__ = (Index("ix_tasks_queue_state", "queue", "state"),)
