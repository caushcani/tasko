"""Seed tasko-core with sample workers and tasks for local development.

    uv run tasko-seed

Writes against whatever ``tasko.yaml`` (or ``$TASKO_CONFIG``) points at —
same resolution as the server itself. Idempotent: every row uses a fixed id,
so re-running updates them in place instead of piling up duplicates.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from tasko_core.infrastructure.config import load_config
from tasko_core.infrastructure.database.session import (
    create_all,
    dispose_engine,
    init_engine,
    session_scope,
)
from tasko_core.modules.tasks.enums import TaskState
from tasko_core.modules.tasks.models import TaskRecord
from tasko_core.modules.workers.models import WorkerRecord

_NOW = datetime.now(UTC)


def _ago(**kwargs: float) -> datetime:
    return _NOW - timedelta(**kwargs)


WORKERS: list[dict[str, Any]] = [
    {"id": "worker-01", "queues": ["reports"], "active_tasks": 1},
    {"id": "worker-02", "queues": ["emails"], "active_tasks": 0},
    {"id": "worker-03", "queues": ["default"], "active_tasks": 0},
    {"id": "worker-04", "queues": ["priority", "maintenance"], "active_tasks": 2},
]

TASKS: list[dict[str, Any]] = [
    {
        "id": "seed-1",
        "name": "sync_customer_records",
        "queue": "default",
        "state": TaskState.SUCCESS,
        "worker_id": "worker-03",
        "execution_ms": 1240,
        "finished_at": _ago(seconds=12),
    },
    {
        "id": "seed-2",
        "name": "generate_weekly_report",
        "queue": "reports",
        "state": TaskState.STARTED,
        "worker_id": "worker-01",
        "started_at": _ago(seconds=42),
    },
    {
        "id": "seed-3",
        "name": "send_invoice_email",
        "queue": "emails",
        "state": TaskState.SUCCESS,
        "worker_id": "worker-02",
        "execution_ms": 820,
        "finished_at": _ago(minutes=1),
    },
    {
        "id": "seed-4",
        "name": "refresh_product_cache",
        "queue": "priority",
        "state": TaskState.FAILURE,
        "worker_id": "worker-04",
        "execution_ms": 4610,
        "traceback": "Traceback (most recent call last):\nValueError: boom",
        "finished_at": _ago(minutes=2),
    },
    {
        "id": "seed-5",
        "name": "rebuild_search_index",
        "queue": "maintenance",
        "state": TaskState.QUEUED,
        "queued_at": _ago(minutes=3),
    },
    {
        "id": "seed-6",
        "name": "send_invoice_email",
        "queue": "emails",
        "state": TaskState.RETRY,
        "worker_id": "worker-02",
        "retries": 1,
        "traceback": "Traceback (most recent call last):\nTimeoutError: upstream",
        "finished_at": _ago(minutes=5),
    },
    {
        "id": "seed-7",
        "name": "sync_customer_records",
        "queue": "default",
        "state": TaskState.SUCCESS,
        "worker_id": "worker-03",
        "execution_ms": 980,
        "finished_at": _ago(hours=1),
    },
    {
        "id": "seed-8",
        "name": "nightly_rollup",
        "queue": "reports",
        "state": TaskState.SUCCESS,
        "worker_id": "worker-01",
        "execution_ms": 15300,
        "finished_at": _ago(hours=3),
    },
]


async def seed() -> None:
    config = load_config()
    init_engine(config.database.url)
    await create_all()

    async with session_scope() as session:
        for w in WORKERS:
            record = await session.get(WorkerRecord, w["id"])
            if record is None:
                record = WorkerRecord(id=w["id"])
                session.add(record)
            record.queues = w["queues"]
            record.active_tasks = w["active_tasks"]
            record.last_heartbeat_at = _NOW

        for t in TASKS:
            record = await session.get(TaskRecord, t["id"])
            if record is None:
                record = TaskRecord(id=t["id"], name=t["name"], queue=t["queue"], state=t["state"])
                session.add(record)
            record.name = t["name"]
            record.queue = t["queue"]
            record.state = t["state"]
            record.worker_id = t.get("worker_id")
            record.retries = t.get("retries", 0)
            record.execution_ms = t.get("execution_ms")
            record.traceback = t.get("traceback")
            record.queued_at = t.get("queued_at")
            record.started_at = t.get("started_at")
            record.finished_at = t.get("finished_at")
            record.args = t.get("args", [])
            record.kwargs = t.get("kwargs", {})

    print(f"Seeded {len(WORKERS)} workers and {len(TASKS)} tasks into {config.database.url}")
    await dispose_engine()


def run() -> None:
    """Console-script entrypoint: ``tasko-seed``."""
    asyncio.run(seed())


if __name__ == "__main__":
    run()
