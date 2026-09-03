# Tasko

A broker-agnostic observability dashboard for [Taskiq](https://taskiq-python.github.io/)
fleets. Tasko ingests task lifecycle events through a `TaskiqMiddleware`, stores
them, and serves a live REST/WebSocket API consumed by a Next.js dashboard.

> Prototype. v1 scope: `tasko-core` + `tasko-middleware` + `tasko-redis` + `web`.

## Layout

| Path                          | What                                                        |
| ----------------------------- | ---------------------------------------------------------- |
| `packages/tasko-core`         | FastAPI server: ingest API, REST/WS, adapter registry      |
| `packages/tasko-middleware`   | `TaskiqMiddleware` subclass that reports events to core    |
| `packages/tasko-redis`        | `BrokerAdapter` implementation for Redis (v1 target)       |
| `packages/tasko-rabbitmq`     | `BrokerAdapter` stub (later / contributors)                |
| `packages/tasko-nats`         | `BrokerAdapter` stub (later / contributors)                |
| `web/`                        | Next.js SSR dashboard                                       |
| `docker/`                     | Dockerfiles + `docker-compose.yml` (core + web + postgres) |

`packages/` and `web/` are independent toolchains — `uv` never touches `web/`,
`pnpm` never touches `packages/`.

## Develop

### Python workspace

```bash
# install uv: https://docs.astral.sh/uv/getting-started/installation/
uv sync                       # one venv, one lockfile, whole workspace
uv run tasko-core             # start the server on :8000
uv run pytest                 # run the test suite
uv run ruff check .           # lint
```

### Web dashboard

```bash
cd web
pnpm install
pnpm dev                      # http://localhost:3000
```

### Everything at once

```bash
docker compose -f docker/docker-compose.yml up --build
```

## Writing a broker adapter

See [docs/writing-a-broker-adapter.md](docs/writing-a-broker-adapter.md).
