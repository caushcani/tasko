"""Request/response models for the tasks module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from tasko_core.modules.tasks.enums import TaskState


class TaskEvent(BaseModel):
    """One lifecycle transition reported by ``tasko-middleware``."""

    task_id: str
    name: str
    queue: str
    state: TaskState
    worker_id: str | None = None
    args: list = Field(default_factory=list)
    kwargs: dict = Field(default_factory=dict)
    result: dict | None = None
    traceback: str | None = None
    retries: int = 0
    execution_ms: int | None = None
    timestamp: datetime


class TaskOut(BaseModel):
    id: str
    name: str
    queue: str
    state: TaskState
    worker_id: str | None
    retries: int
    execution_ms: int | None
    queued_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class TaskDetailOut(TaskOut):
    args: list
    kwargs: dict
    result: dict | None
    traceback: str | None
