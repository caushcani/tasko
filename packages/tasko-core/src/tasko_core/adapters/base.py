"""The ``BrokerAdapter`` contract.

An adapter gives ``tasko-core`` a broker-agnostic view of **queue depth** — the
one thing Tasko cannot learn from middleware events alone.

Worker liveness is reported to core over HTTP by ``tasko-middleware`` (see the
``workers`` module). :meth:`BrokerAdapter.list_workers` is an *optional* extra:
brokers that natively track their consumers (RabbitMQ, NATS) may override it,
and core merges what it returns with the heartbeat-backed list. The default
returns nothing.

Adapter packages subclass :class:`BrokerAdapter` and expose the subclass through
the ``tasko.adapters`` entry point group, e.g.::

    [project.entry-points."tasko.adapters"]
    redis = "tasko_redis.adapter:RedisAdapter"
"""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class QueueStats:
    name: str
    depth: int
    in_flight: int = 0
    oldest_message_at: datetime | None = None
    extra: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class WorkerInfo:
    id: str
    queues: list[str]
    last_heartbeat_at: datetime
    active_tasks: int = 0
    extra: dict[str, object] = field(default_factory=dict)


class BrokerAdapter(abc.ABC):
    """Read-only introspection of a Taskiq broker backend."""

    #: Short identifier, must match the entry point name.
    name: str = ""

    def __init__(self, **options: object) -> None:
        self.options = options

    async def startup(self) -> None:  # noqa: B027 - optional hook, no-op by default
        """Open connections. Called once on server start."""

    async def shutdown(self) -> None:  # noqa: B027 - optional hook, no-op by default
        """Close connections. Called once on server stop."""

    @abc.abstractmethod
    async def list_queues(self) -> list[QueueStats]:
        """Return current stats for every known queue."""

    async def get_queue(self, name: str) -> QueueStats | None:
        """Stats for one queue by name. Default filters :meth:`list_queues`;
        override if the broker can answer a single-queue query more cheaply."""
        for queue in await self.list_queues():
            if queue.name == name:
                return queue
        return None

    async def list_workers(self) -> list[WorkerInfo]:
        """Workers the broker itself knows about. Optional; default: none.

        Most brokers (e.g. Redis list queues) have no consumer registry — for
        those, leave this alone and rely on middleware heartbeats.
        """
        return []

    async def watch(self) -> AsyncIterator[QueueStats | WorkerInfo]:
        """Optionally stream changes. Default: no push support."""
        return
        yield  # pragma: no cover - makes this an async generator
