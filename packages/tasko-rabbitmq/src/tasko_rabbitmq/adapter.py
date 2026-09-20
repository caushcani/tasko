"""RabbitMQ ``BrokerAdapter``.

Reads queue depth and, for ``list_workers``, live consumers from
RabbitMQ's **HTTP Management API** (the ``rabbitmq_management`` plugin,
enabled by default in the official ``rabbitmq:*-management`` images), not
the AMQP protocol. AMQP has no "list queues" operation: a client can only
ask about a queue it already knows the name of. There's no way to discover
queues blind the way the Redis adapter enumerates keys with ``SCAN`, the
Management API is the only broker-side source for that (and for "who is
consuming", which backs ``list_workers`` below). So this adapter never
opens an AMQP connection at all — it's a thin HTTP client.

``taskiq-aio-pika`` does not prefix queue names the way Taskiq's Redis
broker keys its lists under ``taskiq:*``, a queue is named exactly what
the user's ``Queue(name=...)`` says (default: a single queue named
``"taskiq"``). So unlike Redis's ``queue_prefix`` default, there's no
reliable prefix to assume here: this adapter reports every queue in the
configured vhost unless ``queue_prefix`` is set. Point it at your own
convention if the vhost is shared with non-Taskiq queues, or dedicate a
vhost to Taskiq and leave it unset.

Options (from ``tasko.yaml`` -> ``broker.options``):
    management_url:  base URL of the HTTP Management API
                      (default ``http://localhost:15672``)
    username:         (default ``guest``)
    password:         (default ``guest``)
    vhost:            RabbitMQ virtual host (default ``/``)
    queue_prefix:     only report queues whose name starts with this
                      (default: no filter — every queue in the vhost)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx
from tasko_core.adapters import BrokerAdapter, QueueStats, WorkerInfo


class RabbitMQAdapter(BrokerAdapter):
    name = "rabbitmq"

    def __init__(self, **options: object) -> None:
        super().__init__(**options)
        base = str(options.get("management_url", "http://localhost:15672")).rstrip("/")
        self._vhost = quote(str(options.get("vhost", "/")), safe="")
        self._prefix = options.get("queue_prefix") or None
        self._client = httpx.AsyncClient(
            base_url=base,
            auth=(
                str(options.get("username", "guest")),
                str(options.get("password", "guest")),
            ),
            timeout=5.0,
        )

    async def startup(self) -> None:
        resp = await self._client.get("/api/whoami")
        resp.raise_for_status()

    async def shutdown(self) -> None:
        await self._client.aclose()

    async def list_queues(self) -> list[QueueStats]:
        resp = await self._client.get(f"/api/queues/{self._vhost}")
        resp.raise_for_status()
        out = [
            _to_stats(row)
            for row in resp.json()
            if not self._prefix or row["name"].startswith(self._prefix)
        ]
        out.sort(key=lambda q: q.name)
        return out

    async def get_queue(self, name: str) -> QueueStats | None:
        # A queue outside queue_prefix isn't in scope for this deployment,
        # same as it wouldn't appear in list_queues(), refuse it here too
        # rather than answer for a queue this Tasko instance doesn't own.
        if self._prefix and not name.startswith(self._prefix):
            return None
        resp = await self._client.get(f"/api/queues/{self._vhost}/{quote(name, safe='')}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _to_stats(resp.json())

    async def list_workers(self) -> list[WorkerInfo]:
        """Group live AMQP consumers by connection, the closest thing
        RabbitMQ has to a "worker" from the broker's own point of view. A
        Taskiq worker process holds one robust connection for consuming
        (``AioPikaBroker.read_conn``), so every queue it consumes shows up
        as a separate consumer sharing that connection's name.

        Not currently merged into ``GET /api/workers`` — that endpoint is
        DB-only, fed by tasko-middleware heartbeats (see
        modules/workers/routes.py for why a live adapter merge isn't
        paginable alongside the SQL list). Exposed here per the
        ``BrokerAdapter`` contract for whoever wires an adapter-to-
        ``WorkerRecord`` sync next; the ``id`` here (an AMQP connection
        name) is not the same identity as a middleware-reported
        ``worker_id`` and the two won't line up on their own.
        """
        resp = await self._client.get(f"/api/consumers/{self._vhost}")
        resp.raise_for_status()

        by_connection: dict[str, set[str]] = {}
        for row in resp.json():
            conn_name = row["channel_details"]["connection_name"]
            by_connection.setdefault(conn_name, set()).add(row["queue"]["name"])

        now = datetime.now(UTC)
        return [
            WorkerInfo(id=conn_name, queues=sorted(queues), last_heartbeat_at=now)
            for conn_name, queues in sorted(by_connection.items())
        ]


def _to_stats(row: dict[str, Any]) -> QueueStats:
    return QueueStats(
        name=row["name"],
        depth=row.get("messages_ready", 0),
        in_flight=row.get("messages_unacknowledged", 0),
        # No oldest-message timestamp in the Management API response, left
        # at the QueueStats default (None), same as the Redis adapter.
        extra={"consumers": row.get("consumers", 0), "state": row.get("state", "unknown")},
    )
