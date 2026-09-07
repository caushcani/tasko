"""Response models for the stats module — the numbers behind the Overview page."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Metric(BaseModel):
    """A single headline number plus the same number over the preceding window
    of equal length, so the UI can render a delta."""

    value: float
    previous: float


class OverviewOut(BaseModel):
    #: terminal (success + failure) tasks that finished in the last 24h
    tasks_processed: Metric
    #: successes / (successes + failures), 0..1, over the last 24h
    success_rate: Metric
    #: mean execution_ms of tasks that finished in the last 24h
    avg_duration_ms: Metric
    #: workers whose last heartbeat is within the liveness TTL
    workers_online: int
    #: distinct workers seen ever (the "/ N" denominator)
    workers_known: int


class ThroughputBucket(BaseModel):
    start: datetime
    completed: int
    failed: int


class ThroughputOut(BaseModel):
    window: str
    bucket_seconds: int
    buckets: list[ThroughputBucket]
    total_completed: int
    total_failed: int
