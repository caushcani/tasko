"""Seed tasko-core with sample data for local development.

    uv run tasko-seed            # upsert the sample rows
    uv run tasko-seed --reset    # wipe first, then seed

Writes tasks + workers into whatever ``tasko.yaml`` (or ``$TASKO_CONFIG``)
points at, and — when the broker is Redis — pushes dummy payloads onto the
list keys so ``GET /api/queues`` shows depth. Idempotent: fixed ids for the
DB rows, and queue keys are topped up to a target depth rather than appended
to blindly.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete

from tasko_core.infrastructure.config import Config, load_config
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

# queue name -> target depth (items pushed onto the broker's list key)
QUEUES: dict[str, int] = {
    "default": 34,
    "emails": 12,
    "reports": 3,
    "priority": 0,
    "maintenance": 1,
}


def _ago(**kwargs: float) -> datetime:
    return _NOW - timedelta(**kwargs)


WORKERS: list[dict[str, Any]] = [
    {"id": "worker-01", "queues": ["reports"], "active_tasks": 1},
    {"id": "worker-02", "queues": ["emails"], "active_tasks": 0},
    {"id": "worker-03", "queues": ["default"], "active_tasks": 0},
    {"id": "worker-04", "queues": ["priority", "maintenance"], "active_tasks": 2},
]

# (name, queue, worker, kwargs) templates the generator cycles through.
_TEMPLATES: list[tuple[str, str, str, dict[str, Any]]] = [
    ("sync_customer_records", "default", "worker-03", {"since": "2026-09-01", "batch": 500}),
    ("send_invoice_email", "emails", "worker-02", {"invoice_id": 4823, "to": "acme@example.com"}),
    ("generate_weekly_report", "reports", "worker-01", {"org_id": 17, "week": "2026-W36"}),
    ("refresh_product_cache", "priority", "worker-04", {"product_id": 91823}),
    ("rebuild_search_index", "maintenance", "worker-04", {"index": "products", "full": True}),
    ("nightly_rollup", "reports", "worker-01", {"date": "2026-09-04"}),
    ("resize_uploaded_image", "default", "worker-03", {"upload_id": "u_7f3a", "sizes": [128, 512]}),
    (
        "charge_subscription",
        "priority",
        "worker-04",
        {"subscription_id": 20551, "amount_cents": 4900},
    ),
]

_TRACEBACKS = [
    'Traceback (most recent call last):\n  File "tasks.py", line 42, in run\n'
    "    resp.raise_for_status()\nhttpx.HTTPStatusError: 503 Service Unavailable",
    'Traceback (most recent call last):\n  File "tasks.py", line 88, in run\n'
    "    record = Product.objects.get(pk=pid)\nProduct.DoesNotExist: no row for pk=91823",
]


def _build_tasks() -> list[dict[str, Any]]:
    """~24 rows: mostly successes, a couple failures/retries, one running,
    one queued — most recent first, spread back over the last few hours."""
    rows: list[dict[str, Any]] = []
    minutes_ago = 0.0
    for i in range(24):
        name, queue, worker, kwargs = _TEMPLATES[i % len(_TEMPLATES)]
        minutes_ago += 2 + (i % 5) * 3.5
        exec_ms = 180 + (i * 137) % 4200
        started = _ago(minutes=minutes_ago)
        finished = started + timedelta(milliseconds=exec_ms)
        row: dict[str, Any] = {
            "id": f"seed-{i + 1:02d}",
            "name": name,
            "queue": queue,
            "worker_id": worker,
            "kwargs": kwargs,
            "started_at": started,
        }
        if i == 0:
            row |= {"state": TaskState.STARTED, "started_at": _ago(seconds=25), "updated_at": _NOW}
        elif i == 1:
            row |= {
                "state": TaskState.QUEUED,
                "worker_id": None,
                "started_at": None,
                "queued_at": _ago(seconds=50),
                "updated_at": _ago(seconds=50),
            }
        elif i in (5, 17):
            row |= {
                "state": TaskState.FAILURE,
                "execution_ms": exec_ms,
                "traceback": _TRACEBACKS[i % len(_TRACEBACKS)],
                "finished_at": finished,
                "updated_at": finished,
            }
        elif i == 9:
            row |= {
                "state": TaskState.RETRY,
                "retries": 2,
                "traceback": _TRACEBACKS[1],
                "finished_at": finished,
                "updated_at": finished,
            }
        else:
            row |= {
                "state": TaskState.SUCCESS,
                "execution_ms": exec_ms,
                "finished_at": finished,
                "updated_at": finished,
            }
        rows.append(row)
    return rows


TASKS: list[dict[str, Any]] = _build_tasks()


async def seed(*, reset: bool = False) -> None:
    config = load_config()
    init_engine(config.database.url)
    await create_all()

    async with session_scope() as session:
        if reset:
            await session.execute(delete(TaskRecord))
            await session.execute(delete(WorkerRecord))

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
            if "updated_at" in t:
                record.updated_at = t["updated_at"]

    verb = "Reset and seeded" if reset else "Seeded"
    print(f"{verb} {len(WORKERS)} workers and {len(TASKS)} tasks into {config.database.url}")
    print(await _seed_redis_queues(config, reset=reset))
    await dispose_engine()


async def _seed_redis_queues(config: Config, *, reset: bool) -> str:
    """RPUSH placeholder payloads onto the broker's list keys so the queues
    view has depth to show. Redis only; a no-op (with a note) otherwise."""
    if config.broker.adapter != "redis":
        return f"  queues: skipped — broker is {config.broker.adapter!r}, not redis"
    url = str(config.broker.options.get("url", "redis://localhost:6379/0"))
    prefix = str(config.broker.options.get("queue_prefix", "taskiq"))
    try:
        import redis.asyncio as redis
    except ImportError:
        return "  queues: skipped — redis client not installed"

    client = redis.from_url(url)
    try:
        await client.ping()
    except Exception:
        await client.aclose()
        return f"  queues: skipped — can't reach redis at {url}"

    for name, depth in QUEUES.items():
        key = f"{prefix}:{name}"
        if reset:
            await client.delete(key)
        missing = depth - await client.llen(key)
        if missing > 0:
            await client.rpush(key, *([b'{"seed": true}'] * missing))
    await client.aclose()
    return f"  queues: topped up {len(QUEUES)} keys in {url}"


def run() -> None:
    """Console-script entrypoint: ``tasko-seed``."""
    parser = argparse.ArgumentParser(description="Seed tasko-core with sample data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete tasks + workers and clear queue keys before seeding",
    )
    args = parser.parse_args()
    asyncio.run(seed(reset=args.reset))


if __name__ == "__main__":
    run()
