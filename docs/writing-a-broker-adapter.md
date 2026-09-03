# Writing a broker adapter

A `BrokerAdapter` gives `tasko-core` a broker-agnostic view of **queue depth** —
how many messages are waiting, per queue. That's the one thing Tasko can't learn
any other way.

Task lifecycle data (args, result, traceback, timings) and **worker liveness**
come in separately through `tasko-middleware`, over HTTP — an adapter never
handles those. The one exception: `list_workers()` is an *optional* override for
brokers that natively track their consumers (RabbitMQ, NATS). Redis and other
plain queue brokers leave it alone, and core serves workers from middleware
heartbeats.

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

## Reference implementation

`packages/tasko-redis/src/tasko_redis/adapter.py` is the canonical example:
queue depth from `LLEN` on Taskiq's list keys, and no `list_workers` override
(Redis lists have no consumer registry).
