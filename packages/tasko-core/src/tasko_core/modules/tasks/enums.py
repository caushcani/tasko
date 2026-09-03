from __future__ import annotations

import enum


class TaskState(enum.StrEnum):
    QUEUED = "queued"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
