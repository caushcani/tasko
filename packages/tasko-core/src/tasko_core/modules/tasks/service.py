"""Business logic for the tasks module — event ingestion and querying."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tasko_core.infrastructure.database import run_list_query
from tasko_core.modules.common.pagination import ListParams
from tasko_core.modules.tasks.enums import TaskState
from tasko_core.modules.tasks.models import TASK_LIST_SPEC, TaskRecord
from tasko_core.modules.tasks.schemas import TaskEvent

_TERMINAL = {TaskState.SUCCESS, TaskState.FAILURE}

_MAX_DEPTH = 64

_GRAPH_COLS = "id, name, state, queue, parent_task_id, started_at, finished_at, execution_ms"
_GRAPH_COLS_T = ", ".join(f"t.{c}" for c in _GRAPH_COLS.split(", "))

# Walk parent_task_id BOTH ways from :task_id in one recursive term (the join
# condition goes up *or* down) so siblings-of-ancestors are reached too. One
# recursive self-reference, because Postgres rejects a CTE whose recursive
# term is itself a `UNION` of two recursive selects. `UNION` (not `UNION ALL`)
# drops exact-duplicate rows — revisiting a node yields a byte-identical row,
# so a cycle (a task that `.kiq()`s itself) terminates naturally; the depth
# guard is a hard ceiling on top. Only graph columns — never the JSON blobs,
# which Postgres can't `DISTINCT` on.
_LINEAGE_SQL = text(
    f"""
    WITH RECURSIVE lineage(id, name, state, queue, parent_task_id,
                           started_at, finished_at, execution_ms, depth) AS (
        SELECT {_GRAPH_COLS}, 0 FROM tasks WHERE id = :task_id
        UNION
        SELECT {_GRAPH_COLS_T}, l.depth + 1
        FROM tasks t
        JOIN lineage l ON t.id = l.parent_task_id OR t.parent_task_id = l.id
        WHERE l.depth < {_MAX_DEPTH}
    )
    SELECT DISTINCT {_GRAPH_COLS} FROM lineage
    """
)


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
    record.schedule_id = event.schedule_id or record.schedule_id
    record.parent_task_id = event.parent_task_id or record.parent_task_id
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
    name: str | None = None,
    state: TaskState | None = None,
    queue: str | None = None,
    worker_id: str | None = None,
    schedule_id: str | None = None,
    parent_task_id: str | None = None,
) -> tuple[list[TaskRecord], int]:
    """Filtered / sorted / searched / paginated page of tasks, plus total count."""
    filters = {
        k: v
        for k, v in {
            "name": name,
            "state": state,
            "queue": queue,
            "worker_id": worker_id,
            "schedule_id": schedule_id,
            "parent_task_id": parent_task_id,
        }.items()
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


async def get_task_lineage(session: AsyncSession, task_id: str) -> list:
    """Every task connected to ``task_id`` by a parent/child chain, both
    directions. Rows are ``RowMapping``s with the graph columns only. Empty
    if ``task_id`` isn't known."""
    result = await session.execute(_LINEAGE_SQL, {"task_id": task_id})
    return list(result.mappings().all())
