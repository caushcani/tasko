# Writing a broker adapter

A `BrokerAdapter` gives `tasko-core` a broker-agnostic view of **queue depth** —
how many messages are waiting, per queue. That's the one thing Tasko can't learn
any other way.

Task lifecycle data (args, result, traceback, timings) and **worker liveness**
come in separately through `tasko-middleware`, over HTTP — an adapter never
handles those. The one exception: `list_workers()` is an *optional* override
for a broker that can **cheaply** tell individual worker connections apart —
RabbitMQ's Management API does (see its reference implementation below).
Don't assume your broker can just because it "natively tracks consumers" in
some sense: NATS JetStream tracks consumer *objects*, but a durable consumer
is shared by every worker process attached to it, so JetStream's own API
can't tell you which one is which — actually distinguishing connections needs
its separate, non-default monitoring HTTP endpoint, not worth requiring for
this. Redis and NATS both leave `list_workers` at the default; core serves
workers from middleware heartbeats regardless.

## 1. Create a package

Add a directory under `packages/` — do **not** edit `tasko-core`.

```
packages/tasko-mybroker/
├── pyproject.toml
└── src/tasko_mybroker/
    ├── __init__.py
    └── adapter.py
```

`pyproject.toml` declares the dependency on `tasko-core` and registers the
adapter in the `tasko.adapters` entry point group:

```toml
[project]
name = "tasko-mybroker"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["tasko-core", "mybroker-client>=1.0"]

[project.entry-points."tasko.adapters"]
mybroker = "tasko_mybroker.adapter:MyBrokerAdapter"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

The entry point **name** (`mybroker`) is what users put in `tasko.yaml` under
`broker.adapter`, and it must equal the class's `name` attribute.

## 2. Implement `BrokerAdapter`

```python
from tasko_core.adapters import BrokerAdapter, QueueStats


class MyBrokerAdapter(BrokerAdapter):
    name = "mybroker"

    async def startup(self) -> None:
        self._conn = await mybroker.connect(self.options["url"])

    async def shutdown(self) -> None:
        await self._conn.close()

    async def list_queues(self) -> list[QueueStats]: ...

    # Optional — only if your broker knows its consumers:
    # async def list_workers(self) -> list[WorkerInfo]: ...
```

`list_queues` is the only required method. `self.options` is whatever the user
put under `broker.options` in `tasko.yaml`.

`startup` / `shutdown` are called once each, around the server lifespan.
`watch()` is optional — override it to push `QueueStats` / `WorkerInfo` updates
as an async generator; the default yields nothing and core falls back to
polling.

## 3. Wire it up

```bash
uv sync                       # picks up the new workspace member
```

```yaml
# tasko.yaml
broker:
  adapter: mybroker
  options:
    url: mybroker://localhost:1234
```

`GET /healthz` lists every discovered adapter — use it to confirm registration.

## Reference implementations

Three, covering the shapes a broker tends to have. Check what your broker's
own protocol can and can't do (a real server, not the docs) before assuming
any of these patterns transfers — every fact below came from doing exactly
that, not from reading the broker's marketing copy:

- `packages/tasko-redis/src/tasko_redis/adapter.py` — a broker whose native
  protocol can enumerate queues blind (`SCAN` over Taskiq's list keys) and
  has no consumer registry, so `list_workers` is left at the default.
- `packages/tasko-rabbitmq/src/tasko_rabbitmq/adapter.py` — AMQP has no
  "list queues" operation at all (a client can only ask about a queue it
  already knows the name of), so this adapter talks to the broker's **HTTP
  Management API** instead of opening an AMQP connection — bundled and on
  by default in the standard Docker image. That same API is rich enough to
  implement `list_workers` (grouping live consumers by connection). If your
  broker's wire protocol can't enumerate queues either, a management/admin
  HTTP API — if the broker has one, *and* it's the kind of thing a
  self-hoster will actually have turned on — is usually the way in.
- `packages/tasko-nats/src/tasko_nats/adapter.py` — the interesting middle
  case: JetStream's own client protocol *can* enumerate streams blind
  (`streams_info()`, no admin API needed), but only ever reports a real
  backlog for JetStream-backed Taskiq deployments — plain core NATS pub/sub
  has no persistence, so a message with no subscriber is just dropped, and
  there is nothing to report for it. `list_workers` stays at the default
  here despite NATS "tracking consumers": a JetStream durable consumer is a
  shared object every worker process attaches to, so the JetStream API alone
  can't distinguish one worker's connection from another's — that needs
  NATS's separate, non-default monitoring HTTP endpoint. Same broker,
  different scope decision than RabbitMQ, for a documented reason.
