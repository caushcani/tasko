from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WorkerHeartbeat(BaseModel):
    """Periodic liveness ping sent by ``tasko-middleware``."""

    worker_id: str
    queues: list[str] = Field(default_factory=list)
    active_tasks: int = 0


class WorkerOut(BaseModel):
    id: str
    queues: list[str]
    active_tasks: int
    first_seen_at: datetime
    last_heartbeat_at: datetime

    model_config = {"from_attributes": True}
