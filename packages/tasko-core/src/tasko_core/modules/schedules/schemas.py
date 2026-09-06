"""Request/response models for the schedules module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ScheduledTaskIn(BaseModel):
    """One schedule as reported by ``tasko-middleware``'s ``TaskoScheduleSource``
    — a straight projection of taskiq's ``ScheduledTask``."""

    schedule_id: str
    task_name: str
    cron: str | None = None
    cron_offset: str | None = None
    time: datetime | None = None
    #: taskiq allows int seconds or a timedelta; the source normalises to seconds.
    interval_seconds: int | None = None
    args: list = Field(default_factory=list)
    kwargs: dict = Field(default_factory=dict)
    labels: dict = Field(default_factory=dict)


class ScheduleSyncRequest(BaseModel):
    """The full current schedule set for one source. Anything not in the list
    is considered removed from that source."""

    source: str
    schedules: list[ScheduledTaskIn] = Field(default_factory=list)


class ScheduleSyncResult(BaseModel):
    synced: int
    removed: int


class ScheduleOut(BaseModel):
    id: str
    task_name: str
    source: str
    cron: str | None
    cron_offset: str | None
    scheduled_time: datetime | None
    interval_seconds: int | None
    args: list
    kwargs: dict
    labels: dict
    first_seen_at: datetime
    last_seen_at: datetime
    #: derived — most recent run of a task carrying this schedule_id label
    last_fired_at: datetime | None = None
    #: derived — computed from the cron expression / interval / one-off time
    next_fire_at: datetime | None = None

    model_config = {"from_attributes": True}
