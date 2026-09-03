"""Redis ``BrokerAdapter``.

Reports queue depth from Taskiq's list-queue keys. Worker liveness is not a
Redis fact (a list has no consumer registry) — it comes from middleware
heartbeats via ``tasko-core``'s ``workers`` module, so this adapter does not
override ``list_workers``.

Options (from ``tasko.yaml`` -> ``broker.options``):
    url:            redis connection URL (default ``redis://localhost:6379/0``)
    queue_prefix:   key prefix Taskiq publishes to (default ``taskiq``)
"""

from __future__ import annotations

import redis.asyncio as redis
from tasko_core.adapters import BrokerAdapter, QueueStats


class RedisAdapter(BrokerAdapter):
    name = "redis"

    def __init__(self, **options: object) -> None:
        super().__init__(**options)
        self._url = str(options.get("url", "redis://localhost:6379/0"))
        self._prefix = str(options.get("queue_prefix", "taskiq"))
        self._redis: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._redis is None:
            raise RuntimeError("adapter not started")
        return self._redis

    async def startup(self) -> None:
        self._redis = redis.from_url(self._url, decode_responses=True)
        await self._redis.ping()

    async def shutdown(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def list_queues(self) -> list[QueueStats]:
        pattern = f"{self._prefix}:*"
        out: list[QueueStats] = []
        async for key in self.client.scan_iter(match=pattern):
            if await self.client.type(key) != "list":
                continue
            depth = await self.client.llen(key)
            name = key.split(":", 1)[1] if ":" in key else key
            out.append(QueueStats(name=name, depth=depth))
        out.sort(key=lambda q: q.name)
        return out
