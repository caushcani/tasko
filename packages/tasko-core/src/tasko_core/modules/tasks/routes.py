"""HTTP endpoints for the tasks module."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from tasko_core.infrastructure.database import SessionDep
from tasko_core.infrastructure.realtime import hub
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


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(
    session: SessionDep,
    state: TaskState | None = None,
    queue: str | None = None,
    name: str | None = None,
    order: Literal["recent", "slowest"] = "recent",
    limit: int = Query(50, le=500),
    offset: int = 0,
) -> list:
    return await service.query_tasks(
        session,
        state=state,
        queue=queue,
        name=name,
        order=order,
        limit=limit,
        offset=offset,
    )


@router.get("/tasks/{task_id}", response_model=TaskDetailOut)
async def get_task(task_id: str, session: SessionDep):
    record = await service.get_task(session, task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="task not found")
    return record
