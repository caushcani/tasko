"""RabbitMQ ``BrokerAdapter`` — stub.

Not part of v1. See docs/writing-a-broker-adapter.md and use
tasko_redis.adapter.RedisAdapter as the reference implementation.
"""

from __future__ import annotations

from tasko_core.adapters import BrokerAdapter, QueueStats, WorkerInfo


class RabbitMQAdapter(BrokerAdapter):
    name = "rabbitmq"

    async def list_queues(self) -> list[QueueStats]:
        raise NotImplementedError("tasko-rabbitmq is not implemented yet")

    async def list_workers(self) -> list[WorkerInfo]:
        raise NotImplementedError("tasko-rabbitmq is not implemented yet")
