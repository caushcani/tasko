"""Unit tests for the list-query engine, incl. the dotted-relation join path."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tasko_core.infrastructure.database.base import Base
from tasko_core.infrastructure.database.query import BadListField, run_list_query
from tasko_core.modules.tasks.enums import TaskState
from tasko_core.modules.tasks.models import TASK_LIST_SPEC, TaskRecord
from tasko_core.modules.workers.models import WorkerRecord


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest.fixture
async def seeded(session):
    now = datetime.now(UTC)
    session.add_all(
        [
            WorkerRecord(id="w-fresh", last_heartbeat_at=now),
            WorkerRecord(id="w-stale", last_heartbeat_at=now - timedelta(hours=2)),
        ]
    )
    session.add_all(
        [
            TaskRecord(
                id="t1",
                name="send_email",
                queue="emails",
                state=TaskState.SUCCESS,
                worker_id="w-fresh",
                execution_ms=50,
                retries=0,
            ),
            TaskRecord(
                id="t2",
                name="build_report",
                queue="reports",
                state=TaskState.FAILURE,
                worker_id="w-stale",
                execution_ms=900,
                retries=1,
            ),
            TaskRecord(
                id="t3",
                name="send_email",
                queue="emails",
                state=TaskState.SUCCESS,
                worker_id="w-fresh",
                execution_ms=300,
                retries=0,
            ),
            TaskRecord(
                id="t4-no-worker",
                name="orphan",
                queue="reports",
                state=TaskState.QUEUED,
                worker_id=None,
                execution_ms=None,
                retries=0,
            ),
        ]
    )
    await session.flush()
    return session


async def test_filter_and_total(seeded):
    rows, total = await run_list_query(
        seeded, TASK_LIST_SPEC, offset=0, limit=10, filters={"queue": "emails"}
    )
    assert {r.id for r in rows} == {"t1", "t3"}
    assert total == 2


async def test_in_filter_from_list_value(seeded):
    rows, _ = await run_list_query(
        seeded, TASK_LIST_SPEC, offset=0, limit=10, filters={"state": [TaskState.FAILURE]}
    )
    assert [r.id for r in rows] == ["t2"]


async def test_sort_desc_and_pagination(seeded):
    rows, total = await run_list_query(
        seeded,
        TASK_LIST_SPEC,
        offset=1,
        limit=1,
        sort_columns=["execution_ms"],
        sort_orders=["desc"],
    )
    assert [r.id for r in rows] == ["t3"]  # 900, [300], 50, NULL
    assert total == 4


async def test_search_across_columns(seeded):
    rows, _ = await run_list_query(seeded, TASK_LIST_SPEC, offset=0, limit=10, search="report")
    assert [r.id for r in rows] == ["t2"]


async def test_dotted_relation_sort_is_a_left_join(seeded):
    # worker.last_heartbeat_at is on the related WorkerRecord
    rows, total = await run_list_query(
        seeded,
        TASK_LIST_SPEC,
        offset=0,
        limit=10,
        sort_columns=["worker.last_heartbeat_at"],
        sort_orders=["asc"],
    )
    ids = [r.id for r in rows]
    # the worker-less task is NOT dropped by the join
    assert total == 4
    assert "t4-no-worker" in ids
    # t2's worker (stale) sorts before t1/t3's worker (fresh)
    assert ids.index("t2") < ids.index("t1")
    assert ids.index("t2") < ids.index("t3")


async def test_dotted_relation_filter(seeded):
    rows, _ = await run_list_query(
        seeded, TASK_LIST_SPEC, offset=0, limit=10, filters={"worker.id": "w-fresh"}
    )
    assert {r.id for r in rows} == {"t1", "t3"}


async def test_unknown_field_raises(seeded):
    with pytest.raises(BadListField):
        await run_list_query(
            seeded,
            TASK_LIST_SPEC,
            offset=0,
            limit=10,
            sort_columns=["password"],
            sort_orders=["asc"],
        )
    with pytest.raises(BadListField):
        await run_list_query(
            seeded, TASK_LIST_SPEC, offset=0, limit=10, filters={"worker.secret": "x"}
        )


async def test_default_sort_applies_without_sort_param(seeded):
    rows, _ = await run_list_query(seeded, TASK_LIST_SPEC, offset=0, limit=10)
    # default_sort = updated_at desc; just assert we got everything and no error
    assert len(rows) == 4
