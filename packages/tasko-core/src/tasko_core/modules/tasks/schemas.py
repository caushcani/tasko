"""Request/response models for the tasks module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from tasko_core.modules.tasks.enums import TaskState


class TaskEvent(BaseModel):
    """One lifecycle transition reported by ``tasko-middleware``."""

    task_id: str
    name: str
    queue: str
    state: TaskState
    worker_id: str | None = None
    schedule_id: str | None = None
    parent_task_id: str | None = None
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
    schedule_id: str | None
    parent_task_id: str | None
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


class TaskGraphNode(BaseModel):
    id: str
    name: str
    state: TaskState
    queue: str
    parent_task_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    execution_ms: int | None

    model_config = {"from_attributes": True}

    @field_validator("state", mode="before")
    @classmethod
    def _coerce_state(cls, v: object) -> object:
        # the lineage CTE reads `state` via raw SQL, where SQLAlchemy's Enum
        # column holds the member *name* ("SUCCESS"), not its value ("success").
        if isinstance(v, str) and v in TaskState.__members__:
            return TaskState[v]
        return v


class TaskGraphEdge(BaseModel):
    source: str
    target: str


class TaskGraphOut(BaseModel):
    root_id: str
    nodes: list[TaskGraphNode]
    edges: list[TaskGraphEdge]
