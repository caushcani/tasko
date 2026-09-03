"""Business logic for the tasks module — event ingestion and querying."""

from __future__ import annotations

from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasko_core.modules.tasks.enums import TaskState
from tasko_core.modules.tasks.models import TaskRecord
from tasko_core.modules.tasks.schemas import TaskEvent

_TERMINAL = {TaskState.SUCCESS, TaskState.FAILURE}


async def apply_event(session: AsyncSession, event: TaskEvent) -> TaskRecord:
    """Upsert a task record from a lifecycle event and flush it."""
    record = await session.get(TaskRecord, event.task_id)
    if record is None:
        record = TaskRecord(
            id=event.task_id,
            name=event.name,
            queue=event.queue,
            state=event.state,
            retries=0,
            args=[],
            kwargs={},
        )
        session.add(record)

    record.name = event.name
    record.queue = event.queue
    record.state = event.state
    record.worker_id = event.worker_id or record.worker_id
    record.retries = max(record.retries, event.retries)
    if event.args:
        record.args = event.args
    if event.kwargs:
        record.kwargs = event.kwargs
    if event.result is not None:
        record.result = event.result
    if event.traceback is not None:
        record.traceback = event.traceback
    if event.execution_ms is not None:
        record.execution_ms = event.execution_ms

    if event.state is TaskState.QUEUED:
        record.queued_at = event.timestamp
    elif event.state is TaskState.STARTED:
        record.started_at = event.timestamp
    elif event.state in _TERMINAL:
        record.finished_at = event.timestamp

    await session.flush()
    return record


async def query_tasks(
    session: AsyncSession,
    *,
    state: TaskState | None = None,
    queue: str | None = None,
    name: str | None = None,
    order: Literal["recent", "slowest"] = "recent",
    limit: int = 50,
    offset: int = 0,
) -> list[TaskRecord]:
    stmt = select(TaskRecord)
    if state is not None:
        stmt = stmt.where(TaskRecord.state == state)
    if queue is not None:
        stmt = stmt.where(TaskRecord.queue == queue)
    if name is not None:
        stmt = stmt.where(TaskRecord.name == name)
    if order == "slowest":
        stmt = stmt.order_by(TaskRecord.execution_ms.desc().nullslast())
    else:
        stmt = stmt.order_by(TaskRecord.updated_at.desc())
    stmt = stmt.limit(limit).offset(offset)
    return list((await session.scalars(stmt)).all())


async def get_task(session: AsyncSession, task_id: str) -> TaskRecord | None:
    return await session.get(TaskRecord, task_id)
