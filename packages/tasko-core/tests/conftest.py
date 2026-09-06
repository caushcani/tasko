"""Shared fixtures for the tasko-core test suite."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from tasko_core.adapters import BrokerAdapter, QueueStats
from tasko_core.infrastructure.config import Config
from tasko_core.interfaces.main import create_app


class StubAdapter(BrokerAdapter):
    """A broker with one queue and no native consumer registry (like Redis)."""

    name = "stub"

    async def list_queues(self) -> list[QueueStats]:
        return [QueueStats(name="default", depth=3), QueueStats(name="emails", depth=0)]


@pytest.fixture
async def client(monkeypatch, tmp_path):
    monkeypatch.setattr("tasko_core.interfaces.main.load_adapter", lambda *a, **k: StubAdapter())
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    config = Config.model_validate({"database": {"url": db_url}})

    app = create_app(config)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://t") as c,
    ):
        yield c
