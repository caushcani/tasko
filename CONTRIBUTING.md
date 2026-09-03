# Contributing to Tasko

## Prerequisites

- Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/)
- Node ≥ 20 and pnpm (only if touching `web/`)

## Setup

```bash
uv sync
cd web && pnpm install && cd ..
```

## Working across the Python workspace

There is **one venv and one `uv.lock`** for every package under `packages/`.
Run `uv sync` after changing any package's dependencies. Editable installs mean
changes in `tasko-core` are visible to `tasko-redis` immediately — no reinstall.

## `tasko-core` internal layout

Three layers under `src/tasko_core/`:

| Layer | What lives here |
| --- | --- |
| `interfaces/` | How the world talks to the app — `main.py` (the FastAPI app + lifespan) and `api/v1/` (router aggregator + the `/ws` stream). |
| `infrastructure/` | What the app uses — `config.py`, `database/` (engine, session, `Base`), `realtime.py` (the fan-out hub), `broker.py` (the active-adapter dependency). |
| `modules/` | What the app *is* — one vertical slice per feature (`tasks/`, `workers/`, `queues/`), each with its own `models.py` / `schemas.py` / `service.py` / `routes.py` (and `enums.py` where useful). `common/` holds cross-module shared code. |

`adapters/` sits outside those three: it's the **public** `BrokerAdapter`
contract + registry that adapter packages import.

Request flow: `interfaces/api/v1` → `modules/<feature>/routes.py` →
`modules/<feature>/service.py` → `infrastructure/database`.

## Before opening a PR

```bash
uv run ruff check . && uv run ruff format --check .
uv run pytest
cd web && pnpm lint && pnpm build
```

## Adding a broker adapter

Add a new package under `packages/` — do **not** edit `tasko-core`. The adapter
registers itself through the `tasko.adapters` entry point group. Full guide:
[docs/writing-a-broker-adapter.md](docs/writing-a-broker-adapter.md).
