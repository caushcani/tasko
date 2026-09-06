"""HTTP endpoints for the tasks module."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tasko_core.infrastructure.database import SessionDep
from tasko_core.infrastructure.realtime import hub
from tasko_core.modules.common.pagination import ListParamsDep, PaginatedResponse
from tasko_core.modules.tasks import service
from tasko_core.modules.tasks.enums import TaskState
from tasko_core.modules.tasks.schemas import TaskDetailOut, TaskEvent, TaskOut

router = APIRouter(tags=["tasks"])


@router.post("/tasks/events", status_code=202)
async def ingest_event(event: TaskEvent, session: SessionDep) -> dict[str, str]:
    record = await service.apply_event(session, event)
    payload = TaskOut.model_validate(record).model_dump(mode="json")
    await hub.broadcast({"type": "task", "data": payload})
    return {"status": "accepted"}


@router.get("/tasks", response_model=PaginatedResponse[TaskOut])
async def list_tasks(
    params: ListParamsDep,
    session: SessionDep,
    name: str | None = None,
    state: TaskState | None = None,
    queue: str | None = None,
    worker_id: str | None = None,
    schedule_id: str | None = None,
) -> PaginatedResponse[TaskOut]:
    rows, total = await service.list_tasks(
        session,
        params,
        name=name,
        state=state,
        queue=queue,
        worker_id=worker_id,
        schedule_id=schedule_id,
    )
    return PaginatedResponse[TaskOut](
        items=[TaskOut.model_validate(r) for r in rows],
        total_count=total,
        offset=params.offset,
        limit=params.limit,
    )


@router.get("/tasks/{task_id}", response_model=TaskDetailOut)
async def get_task(task_id: str, session: SessionDep):
    record = await service.get_task(session, task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="task not found")
    return record
