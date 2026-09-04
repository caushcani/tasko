"""Business logic for the tasks module — event ingestion and querying."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tasko_core.infrastructure.database import run_list_query
from tasko_core.modules.common.pagination import ListParams
from tasko_core.modules.tasks.enums import TaskState
from tasko_core.modules.tasks.models import TASK_LIST_SPEC, TaskRecord
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


async def list_tasks(
    session: AsyncSession,
    params: ListParams,
    *,
    state: TaskState | None = None,
    queue: str | None = None,
    worker_id: str | None = None,
) -> tuple[list[TaskRecord], int]:
    """Filtered / sorted / searched / paginated page of tasks, plus total count."""
    filters = {
        k: v
        for k, v in {"state": state, "queue": queue, "worker_id": worker_id}.items()
        if v is not None
    }
    return await run_list_query(
        session,
        TASK_LIST_SPEC,
        offset=params.offset,
        limit=params.limit,
        sort_columns=params.sort_columns,
        sort_orders=params.sort_orders,
        search=params.search,
        filters=filters,
    )


async def get_task(session: AsyncSession, task_id: str) -> TaskRecord | None:
    return await session.get(TaskRecord, task_id)
