"""A ``TaskiqMiddleware`` that reports to ``tasko-core``.

Usage in your worker::

    from taskiq_redis import ListQueueBroker
    from tasko_middleware import TaskoMiddleware

    broker = ListQueueBroker("redis://localhost:6379").with_middlewares(
        TaskoMiddleware(core_url="http://localhost:8000"),
    )

Two things flow to core, both over HTTP:

* task lifecycle events (``POST /api/tasks/events``) — one per transition
* worker heartbeats (``POST /api/workers/heartbeat``) — on a timer, worker
  processes only

The middleware is broker-agnostic: it only reads what Taskiq hands every
middleware hook, and never talks to the broker directly.

It also captures **task lineage** — which task triggered which. When a task is
running and its code calls ``other_task.kiq(...)``, the ``pre_send`` hook stamps
the running task's id onto the new message's labels as ``parent_task_id``. No
user code changes; works for any ``.kiq()`` / ``.kicker()`` / ``broker.kick()``
path since they all pass through ``pre_send``.
"""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import os
import time
import traceback as tb_module
from datetime import UTC, datetime
from typing import Any

import httpx
from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult

#: The id of the task currently executing in this asyncio task. taskiq runs each
#: message in its own ``asyncio.create_task``, which copies the context, so a
#: ``.set()`` here is isolated to one task and never leaks to siblings.
_current_task_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tasko_current_task_id", default=None
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _queue_of(message: TaskiqMessage) -> str:
    labels = message.labels or {}
    return str(labels.get("queue") or labels.get("broker") or "default")


def _schedule_id_of(message: TaskiqMessage) -> str | None:
    """The scheduler stamps this label on every task it kicks (see
    ``TaskiqScheduler.on_ready``); absent for tasks kicked by hand."""
    value = (message.labels or {}).get("schedule_id")
    return str(value) if value is not None else None


def _parent_task_id_of(message: TaskiqMessage) -> str | None:
    value = (message.labels or {}).get("parent_task_id")
    return str(value) if value is not None else None


class TaskoMiddleware(TaskiqMiddleware):
    def __init__(
        self,
        core_url: str = "http://localhost:8000",
        *,
        worker_id: str | None = None,
        heartbeat_interval: float = 10.0,
        timeout: float = 2.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__()
        base = core_url.rstrip("/")
        self._events_url = f"{base}/api/tasks/events"
        self._heartbeat_url = f"{base}/api/workers/heartbeat"
        self._worker_id = worker_id or os.environ.get("TASKO_WORKER_ID") or f"worker-{os.getpid()}"
        self._heartbeat_interval = heartbeat_interval
        self._client = client or httpx.AsyncClient(timeout=timeout)

        self._inflight: dict[str, float] = {}  # task_id -> monotonic start
        self._queues_seen: set[str] = set()
        self._heartbeat_task: asyncio.Task[None] | None = None

    async def _post(self, url: str, payload: dict[str, Any]) -> None:
        # Observability must never break the worker. Drop on any error.
        with contextlib.suppress(httpx.HTTPError):
            await self._client.post(url, json=payload)

    async def _emit(self, payload: dict[str, Any]) -> None:
        payload.setdefault("timestamp", _now())
        payload.setdefault("worker_id", self._worker_id)
        await self._post(self._events_url, payload)

    # --- lifecycle ------------------------------------------------------------

    async def startup(self) -> None:
        if getattr(self.broker, "is_worker_process", False):
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def shutdown(self) -> None:
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
        await self._client.aclose()

    async def _heartbeat_loop(self) -> None:
        while True:
            await self._send_heartbeat()
            await asyncio.sleep(self._heartbeat_interval)

    async def _send_heartbeat(self) -> None:
        await self._post(
            self._heartbeat_url,
            {
                "worker_id": self._worker_id,
                "queues": sorted(self._queues_seen),
                "active_tasks": len(self._inflight),
            },
        )

    # --- Taskiq hooks -------------------------------------------------------

    async def pre_send(self, message: TaskiqMessage) -> TaskiqMessage:
        # Client-side, right before the message goes to the broker. If a task is
        # running right now (its code called `.kiq()`), record it as the parent.
        parent_id = _current_task_id.get()
        if parent_id and "parent_task_id" not in (message.labels or {}):
            message.labels = {**(message.labels or {}), "parent_task_id": parent_id}
        return message

    async def post_send(self, message: TaskiqMessage) -> None:
        await self._emit(
            {
                "task_id": message.task_id,
                "name": message.task_name,
                "queue": _queue_of(message),
                "schedule_id": _schedule_id_of(message),
                "parent_task_id": _parent_task_id_of(message),
                "state": "queued",
                "args": list(message.args),
                "kwargs": dict(message.kwargs),
            }
        )

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        _current_task_id.set(message.task_id)
        self._inflight[message.task_id] = time.monotonic()
        self._queues_seen.add(_queue_of(message))
        await self._emit(
            {
                "task_id": message.task_id,
                "name": message.task_name,
                "queue": _queue_of(message),
                "schedule_id": _schedule_id_of(message),
                "parent_task_id": _parent_task_id_of(message),
                "state": "started",
            }
        )
        return message

    async def post_execute(self, message: TaskiqMessage, result: TaskiqResult[Any]) -> None:
        started = self._inflight.pop(message.task_id, None)
        execution_ms = int((time.monotonic() - started) * 1000) if started is not None else None

        payload: dict[str, Any] = {
            "task_id": message.task_id,
            "name": message.task_name,
            "queue": _queue_of(message),
            "schedule_id": _schedule_id_of(message),
            "state": "failure" if result.is_err else "success",
            "execution_ms": execution_ms,
        }
        if result.is_err and result.error is not None:
            payload["traceback"] = "".join(
                tb_module.format_exception(
                    type(result.error), result.error, result.error.__traceback__
                )
            )
        else:
            payload["result"] = {"value": _safe(result.return_value)}
        await self._emit(payload)

    async def on_error(
        self, message: TaskiqMessage, result: TaskiqResult[Any], exception: BaseException
    ) -> None:
        self._inflight.pop(message.task_id, None)
        await self._emit(
            {
                "task_id": message.task_id,
                "name": message.task_name,
                "queue": _queue_of(message),
                "schedule_id": _schedule_id_of(message),
                "state": "retry",
                "traceback": "".join(
                    tb_module.format_exception(type(exception), exception, exception.__traceback__)
                ),
            }
        )


def _safe(value: Any) -> Any:
    """Best-effort JSON-friendly rendering of a return value."""
    try:
        import json

        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)
