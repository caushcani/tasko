"""Unit tests for the tasks module service layer — no HTTP, no real broker."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tasko_core.infrastructure.database.base import Base
from tasko_core.modules.tasks import service
from tasko_core.modules.tasks.enums import TaskState
from tasko_core.modules.tasks.models import TaskRecord  # noqa: F401 - registers the table
from tasko_core.modules.tasks.schemas import TaskEvent


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _event(**over) -> TaskEvent:
    base = {
        "task_id": "t1",
        "name": "app.tasks.do_thing",
        "queue": "default",
        "state": TaskState.QUEUED,
        "timestamp": datetime.now(UTC),
    }
    return TaskEvent(**{**base, **over})


async def test_apply_event_upserts_and_advances_state(session):
    await service.apply_event(session, _event(state=TaskState.QUEUED))
    rec = await service.apply_event(session, _event(state=TaskState.SUCCESS, execution_ms=120))
    assert rec.state is TaskState.SUCCESS
    assert rec.execution_ms == 120
    assert rec.queued_at is not None and rec.finished_at is not None


async def test_query_tasks_filters_by_state(session):
    await service.apply_event(session, _event(task_id="ok", state=TaskState.SUCCESS))
    await service.apply_event(session, _event(task_id="bad", state=TaskState.FAILURE))
    failures = await service.query_tasks(session, state=TaskState.FAILURE)
    assert [r.id for r in failures] == ["bad"]
