"""Seed tasko-core with sample data for local development.

    uv run tasko-seed            # upsert the sample rows
    uv run tasko-seed --reset    # wipe first, then seed

Writes tasks + workers + schedules into whatever ``tasko.yaml`` (or
``$TASKO_CONFIG``) points at, links some task runs back to a schedule, and —
when the broker is Redis — pushes dummy payloads onto the
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
from tasko_core.modules.alerts.enums import (
    ChannelType,
    ComparisonOperator,
    RuleState,
    RuleType,
    ScopeType,
    Severity,
)
from tasko_core.modules.alerts.models import AlertEvent, AlertRule, NotificationChannel
from tasko_core.modules.schedules.models import ScheduleRecord
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

# Schedules, and the task name each one fires. A run whose task name matches
# is linked back (every other occurrence) so schedule detail pages have a
# "recent runs" list and the rest look hand-kicked.
SCHEDULES: list[dict[str, Any]] = [
    {
        "id": "sch-nightly-rollup",
        "task_name": "nightly_rollup",
        "cron": "0 2 * * *",
        "source": "LabelScheduleSource",
    },
    {
        "id": "sch-weekly-report",
        "task_name": "generate_weekly_report",
        "cron": "0 6 * * 1",
        "source": "LabelScheduleSource",
    },
    {
        "id": "sch-cache-refresh",
        "task_name": "refresh_product_cache",
        "interval_seconds": 300,
        "source": "LabelScheduleSource",
    },
    {
        "id": "sch-search-reindex",
        "task_name": "rebuild_search_index",
        "cron": "*/30 * * * *",
        "source": "LabelScheduleSource",
    },
]
_SCHEDULE_BY_TASK: dict[str, str] = {s["task_name"]: s["id"] for s in SCHEDULES}

# child seed id -> parent seed id, so the task-detail lineage graph has
# something to draw: a chain seed-09 → seed-07 → seed-05 → seed-03 plus a
# fan-out seed-09 → seed-08. Parents are older runs (higher index).
_LINEAGE: dict[str, str] = {
    "seed-03": "seed-05",
    "seed-05": "seed-07",
    "seed-07": "seed-09",
    "seed-08": "seed-09",
}

_TRACEBACKS = [
    'Traceback (most recent call last):\n  File "tasks.py", line 42, in run\n'
    "    resp.raise_for_status()\nhttpx.HTTPStatusError: 503 Service Unavailable",
    'Traceback (most recent call last):\n  File "tasks.py", line 88, in run\n'
    "    record = Product.objects.get(pk=pid)\nProduct.DoesNotExist: no row for pk=91823",
]


def _build_tasks() -> list[dict[str, Any]]:
    """~24 rows: mostly successes, a couple failures/retries, one running,
    one queued — most recent first, spread back over ~the last 18h so the
    Overview throughput chart has a full 24h window to draw."""
    rows: list[dict[str, Any]] = []
    minutes_ago = 0.0
    name_seen: dict[str, int] = {}
    for i in range(24):
        name, queue, worker, kwargs = _TEMPLATES[i % len(_TEMPLATES)]
        name_seen[name] = name_seen.get(name, 0) + 1
        minutes_ago += 12 + (i % 5) * 18
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
        # link every other occurrence of a scheduled task back to its schedule
        if name in _SCHEDULE_BY_TASK and name_seen[name] % 2 == 1:
            row["schedule_id"] = _SCHEDULE_BY_TASK[name]
        if row["id"] in _LINEAGE:
            row["parent_task_id"] = _LINEAGE[row["id"]]
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

    # A thinner batch 25-46h back — outside the throughput chart's 24h window,
    # but it gives the Overview metric cards a real "previous 24h" to diff
    # against instead of everything reading "new".
    for j in range(14):
        name, queue, worker, kwargs = _TEMPLATES[j % len(_TEMPLATES)]
        exec_ms = 200 + (j * 191) % 3800
        started = _ago(minutes=25 * 60 + j * 95)
        finished = started + timedelta(milliseconds=exec_ms)
        failed = j in (3, 11)
        rows.append(
            {
                "id": f"seed-p{j + 1:02d}",
                "name": name,
                "queue": queue,
                "worker_id": worker,
                "kwargs": kwargs,
                "state": TaskState.FAILURE if failed else TaskState.SUCCESS,
                "execution_ms": exec_ms,
                "traceback": _TRACEBACKS[j % len(_TRACEBACKS)] if failed else None,
                "started_at": started,
                "finished_at": finished,
                "updated_at": finished,
            }
        )
    return rows


TASKS: list[dict[str, Any]] = _build_tasks()

# One rule per RuleType. The "default backlog" one genuinely trips against the
# seeded queue depth, so the Alerts page has a live firing alert to show; the
# rest sit OK and the background evaluator keeps them honest.
ALERT_RULES: list[dict[str, Any]] = [
    {
        "id": "rule-default-backlog",
        "name": "Default queue backlog",
        "type": RuleType.QUEUE_BACKLOG,
        "scope": ScopeType.QUEUE,
        "scope_value": "default",
        "operator": ComparisonOperator.GT,
        "threshold": 20,
        "for_seconds": 120,
        "severity": Severity.WARNING,
        "state": RuleState.FIRING,
    },
    {
        "id": "rule-fleet-failure-rate",
        "name": "Fleet failure rate",
        "type": RuleType.FAILURE_RATE,
        "scope": ScopeType.GLOBAL,
        "operator": ComparisonOperator.GT,
        "threshold": 0.2,
        "window_seconds": 3600,
        "for_seconds": 300,
        "severity": Severity.CRITICAL,
    },
    {
        "id": "rule-worker-offline",
        "name": "Worker offline",
        "type": RuleType.WORKER_DOWN,
        "scope": ScopeType.GLOBAL,
        "operator": ComparisonOperator.GTE,
        "threshold": 120,
        "for_seconds": 60,
        "severity": Severity.CRITICAL,
    },
    {
        "id": "rule-stuck-reports",
        "name": "Report task stuck",
        "type": RuleType.STUCK_TASK,
        "scope": ScopeType.QUEUE,
        "scope_value": "reports",
        "operator": ComparisonOperator.GTE,
        "threshold": 900,
        "for_seconds": 0,
        "severity": Severity.WARNING,
    },
]

ALERT_CHANNELS: list[dict[str, Any]] = [
    {
        "id": "chan-ops-webhook",
        "name": "Ops webhook",
        "type": ChannelType.WEBHOOK,
        "enabled": False,
        "config": {"url": "https://example.com/tasko-hook"},
        "min_severity": Severity.WARNING,
    },
]

ALERT_EVENTS: list[dict[str, Any]] = [
    {
        "id": "evt-backlog-active",
        "rule_id": "rule-default-backlog",
        "severity": Severity.WARNING,
        "summary": "Queue backlog (default): 34 > 20",
        "trigger_value": 34.0,
        "started_at": _ago(minutes=8),
        "resolved_at": None,
    },
    {
        "id": "evt-failure-past",
        "rule_id": "rule-fleet-failure-rate",
        "severity": Severity.CRITICAL,
        "summary": "Failure rate: 27.0% > 20.0%",
        "trigger_value": 0.27,
        "started_at": _ago(hours=6),
        "resolved_at": _ago(hours=5, minutes=42),
    },
]


async def seed(*, reset: bool = False) -> None:
    config = load_config()
    init_engine(config.database.url)
    await create_all()

    async with session_scope() as session:
        if reset:
            await session.execute(delete(TaskRecord))
            await session.execute(delete(WorkerRecord))
            await session.execute(delete(ScheduleRecord))
            await session.execute(delete(AlertEvent))
            await session.execute(delete(AlertRule))
            await session.execute(delete(NotificationChannel))

        for s in SCHEDULES:
            record = await session.get(ScheduleRecord, s["id"])
            if record is None:
                record = ScheduleRecord(id=s["id"], task_name=s["task_name"], first_seen_at=_NOW)
                session.add(record)
            record.task_name = s["task_name"]
            record.source = s.get("source", "LabelScheduleSource")
            record.cron = s.get("cron")
            record.interval_seconds = s.get("interval_seconds")
            record.last_seen_at = _NOW

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
            record.schedule_id = t.get("schedule_id")
            record.parent_task_id = t.get("parent_task_id")
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

        for r in ALERT_RULES:
            record = await session.get(AlertRule, r["id"])
            fresh = record is None
            if fresh:
                record = AlertRule(id=r["id"])
                session.add(record)
            record.name = r["name"]
            record.type = r["type"]
            record.scope = r["scope"]
            record.scope_value = r.get("scope_value")
            record.operator = r["operator"]
            record.threshold = r["threshold"]
            record.window_seconds = r.get("window_seconds")
            record.for_seconds = r["for_seconds"]
            record.severity = r["severity"]
            record.enabled = True
            # engine-owned fields: only stamp on first insert / --reset so a
            # re-seed doesn't stomp the live evaluator's state
            if fresh or reset:
                record.state = r.get("state", RuleState.OK)
                record.state_since = _ago(minutes=8)

        for c in ALERT_CHANNELS:
            record = await session.get(NotificationChannel, c["id"])
            if record is None:
                record = NotificationChannel(id=c["id"])
                session.add(record)
            record.name = c["name"]
            record.type = c["type"]
            record.enabled = c["enabled"]
            record.config = c["config"]
            record.min_severity = c["min_severity"]

        for e in ALERT_EVENTS:
            record = await session.get(AlertEvent, e["id"])
            if record is None:
                record = AlertEvent(id=e["id"])
                session.add(record)
            record.rule_id = e["rule_id"]
            record.severity = e["severity"]
            record.summary = e["summary"]
            record.trigger_value = e["trigger_value"]
            record.started_at = e["started_at"]
            record.resolved_at = e["resolved_at"]

    verb = "Reset and seeded" if reset else "Seeded"
    print(
        f"{verb} {len(WORKERS)} workers, {len(TASKS)} tasks, "
        f"{len(SCHEDULES)} schedules and {len(ALERT_RULES)} alert rules "
        f"into {config.database.url}"
    )
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
