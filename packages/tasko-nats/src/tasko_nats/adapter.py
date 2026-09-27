"""NATS ``BrokerAdapter``.

Only meaningful for **JetStream**-backed Taskiq deployments
(``PushBasedJetStreamBroker`` / ``PullBasedJetStreamBroker`` from
``taskiq-nats``) — plain core NATS pub/sub (``NatsBroker``) has no
persistence at all: a message published with nobody currently subscribed is
simply dropped, so there's no backlog to report, ever. ``startup`` fails
loudly if the target server doesn't have JetStream enabled, rather than
quietly reporting zero for everything.

Unlike RabbitMQ, no separate admin HTTP API is needed here: JetStream's own
client protocol can enumerate streams blind (``streams_info()``) over the
same connection used to publish/consume — no management plugin, no second
port or credentials. One Taskiq JetStream broker config maps to one stream
(``stream_name``, default ``"taskiq_jetstream"``) and one subject, so **one
stream = one Tasko queue** — the same granularity as one RabbitMQ
``Queue(name=...)``.

``depth`` / ``in_flight`` come from the stream's consumer(s):
``num_pending`` (not yet delivered to that consumer) and ``num_ack_pending``
(delivered, awaiting ack) — verified against a real ``nats-server -js``.
Taskiq's own broker code always creates exactly one *durable*, name-keyed
consumer per stream, and every worker process for that broker config attaches
to that same shared consumer (that's how they load-balance) — so summing
across a stream's consumers doesn't double-count in the normal case. A
stream nobody has ever consumed from yet has no consumer at all
(``consumers_info`` returns ``[]``); depth then falls back to the stream's
own ``messages`` count, with ``in_flight`` at 0.

Deliberately **no ``list_workers()`` override**: unlike RabbitMQ's Management
API (bundled and on by default in the standard Docker image), telling
individual *connections* apart on NATS needs the server's separate
monitoring HTTP endpoint (``-m``/``http_port``, off by default) —
JetStream's own ``ConsumerInfo`` only knows about the one shared durable
consumer, not which worker process is attached to it. Not worth requiring
extra, non-default server config for v1; Redis's adapter skips it for the
same reason (no consumer registry it can cheaply see).

Options (from ``tasko.yaml`` -> ``broker.options``):
    servers:        NATS server URL or list of URLs
                     (default ``nats://localhost:4222``)
    stream_prefix:  only report streams whose name starts with this
                     (default: no filter — every stream on the account)
    anything else (``user``, ``password``, ``token``, ``tls``, ...) is
    passed straight through to ``nats.connect()``.
"""

from __future__ import annotations

from typing import Any

import nats
from nats.aio.client import Client
from nats.js.api import StreamInfo
from nats.js.client import JetStreamContext
from nats.js.errors import NotFoundError, ServiceUnavailableError
from tasko_core.adapters import BrokerAdapter, QueueStats


class NatsAdapter(BrokerAdapter):
    name = "nats"

    def __init__(self, **options: object) -> None:
        super().__init__(**options)
        opts = dict(options)
        self._servers: str | list[str] = opts.pop("servers", "nats://localhost:4222")  # type: ignore[assignment]
        self._prefix = opts.pop("stream_prefix", None) or None
        self._connect_kwargs: dict[str, Any] = opts
        self._nc: Client | None = None
        self._js: JetStreamContext | None = None

    @property
    def js(self) -> JetStreamContext:
        if self._js is None:
            raise RuntimeError("adapter not started")
        return self._js

    async def startup(self) -> None:
        self._nc = await nats.connect(self._servers, **self._connect_kwargs)
        self._js = self._nc.jetstream()
        try:
            await self._js.account_info()
        except ServiceUnavailableError as exc:
            raise RuntimeError(
                "JetStream is not enabled on this NATS server. Tasko's NATS "
                "adapter needs it to report queue depth, plain core NATS "
                "pub/sub has no persisted backlog to measure. Start "
                "nats-server with -js (or the nats:*-alpine image with -js)."
            ) from exc

    async def shutdown(self) -> None:
        if self._nc is not None:
            await self._nc.close()
            self._nc = None
            self._js = None

    async def list_queues(self) -> list[QueueStats]:
        streams = await self.js.streams_info()
        out = [
            await self._to_stats(stream)
            for stream in streams
            if not self._prefix or stream.config.name.startswith(self._prefix)
        ]
        out.sort(key=lambda q: q.name)
        return out

    async def get_queue(self, name: str) -> QueueStats | None:
        # A stream outside stream_prefix isn't in scope for this deployment,
        # same as it wouldn't appear in list_queues() — refuse it here too.
        if self._prefix and not name.startswith(self._prefix):
            return None
        try:
            stream = await self.js.stream_info(name)
        except NotFoundError:
            return None
        return await self._to_stats(stream)

    async def _to_stats(self, stream: StreamInfo) -> QueueStats:
        name = stream.config.name or ""
        consumers = await self.js.consumers_info(name)
        if not consumers:
            # nobody has ever consumed this stream — no consumer to ask, but
            # everything currently stored is, definitionally, still waiting.
            return QueueStats(name=name, depth=stream.state.messages, extra={"consumers": 0})
        return QueueStats(
            name=name,
            depth=sum(c.num_pending or 0 for c in consumers),
            in_flight=sum(c.num_ack_pending or 0 for c in consumers),
            extra={"consumers": len(consumers)},
        )
