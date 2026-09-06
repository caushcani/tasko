"""A ``ScheduleSource`` wrapper that mirrors schedule definitions to tasko-core.

Taskiq's scheduler takes ``sources``, not middlewares — so this is how Tasko
sees schedules: wrap whatever source(s) you already pass to ``TaskiqScheduler``
and it forwards the current schedule set to ``POST /api/schedules/sync`` on
startup and whenever it changes.

    from taskiq.schedule_sources import LabelScheduleSource
    from taskiq import TaskiqScheduler
    from tasko_middleware import TaskoScheduleSource

    scheduler = TaskiqScheduler(
        broker,
        sources=[TaskoScheduleSource(LabelScheduleSource(broker),
                                     core_url="http://localhost:8000")],
    )

Delegation is total — ``get_schedules`` / ``add_schedule`` / ``delete_schedule``
/ ``pre_send`` / ``post_send`` all pass straight through to the wrapped source.
The scheduler already stamps a ``schedule_id`` label on every task it kicks, so
the schedule → run linkage arrives through the normal task events; nothing extra
is reported from here.
"""

from __future__ import annotations

import contextlib
import json
from datetime import timedelta
from typing import Any

import httpx
from taskiq.abc.schedule_source import ScheduleSource
from taskiq.scheduler.scheduled_task import ScheduledTask


def _interval_seconds(value: int | timedelta | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, timedelta):
        return int(value.total_seconds())
    return int(value)


def _serialize(task: ScheduledTask) -> dict[str, Any]:
    offset = task.cron_offset
    return {
        "schedule_id": task.schedule_id,
        "task_name": task.task_name,
        "cron": task.cron,
        "cron_offset": str(offset) if offset is not None else None,
        "time": task.time.isoformat() if task.time is not None else None,
        "interval_seconds": _interval_seconds(task.interval),
        "args": list(task.args),
        "kwargs": dict(task.kwargs),
        "labels": dict(task.labels),
    }


class TaskoScheduleSource(ScheduleSource):
    def __init__(
        self,
        source: ScheduleSource,
        core_url: str = "http://localhost:8000",
        *,
        source_name: str | None = None,
        timeout: float = 2.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._source = source
        self._sync_url = f"{core_url.rstrip('/')}/api/schedules/sync"
        self._source_name = source_name or type(source).__name__
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._last_sync_fingerprint: str | None = None

    # --- lifecycle -----------------------------------------------------------

    async def startup(self) -> None:
        await self._source.startup()
        with contextlib.suppress(Exception):
            await self._sync(await self._source.get_schedules())

    async def shutdown(self) -> None:
        await self._source.shutdown()
        await self._client.aclose()

    # --- ScheduleSource passthrough ---------------------------------------

    async def get_schedules(self) -> list[ScheduledTask]:
        schedules = await self._source.get_schedules()
        with contextlib.suppress(Exception):
            await self._sync(schedules)
        return schedules

    async def add_schedule(self, schedule: ScheduledTask) -> None:
        await self._source.add_schedule(schedule)

    async def delete_schedule(self, schedule_id: str) -> None:
        await self._source.delete_schedule(schedule_id)

    async def pre_send(self, task: ScheduledTask) -> None:
        await self._source.pre_send(task)

    async def post_send(self, task: ScheduledTask) -> None:
        await self._source.post_send(task)

    # --- sync -------------------------------------------------------------

    async def _sync(self, schedules: list[ScheduledTask]) -> None:
        payload = {
            "source": self._source_name,
            "schedules": [_serialize(t) for t in schedules],
        }
        fingerprint = json.dumps(payload, sort_keys=True, default=str)
        if fingerprint == self._last_sync_fingerprint:
            return
        # Reporting must never break the scheduler.
        with contextlib.suppress(httpx.HTTPError):
            resp = await self._client.post(self._sync_url, json=payload)
            resp.raise_for_status()
            self._last_sync_fingerprint = fingerprint
