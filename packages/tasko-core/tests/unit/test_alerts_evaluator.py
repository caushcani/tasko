"""Unit tests for the alert rule engine — measurement, comparison, state machine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tasko_core.adapters import BrokerAdapter, QueueStats
from tasko_core.infrastructure.database.base import Base
from tasko_core.modules.alerts import evaluator
from tasko_core.modules.alerts.enums import (
    ComparisonOperator,
    RuleState,
    RuleType,
    ScopeType,
    Severity,
)
from tasko_core.modules.alerts.models import AlertEvent, AlertRule
from tasko_core.modules.tasks.enums import TaskState
from tasko_core.modules.tasks.models import TaskRecord
from tasko_core.modules.workers.models import WorkerRecord

_NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


class FakeAdapter(BrokerAdapter):
    name = "fake"

    def __init__(self, depths: dict[str, int]) -> None:
        super().__init__()
        self._depths = depths

    async def list_queues(self) -> list[QueueStats]:
        return [QueueStats(name=n, depth=d) for n, d in self._depths.items()]


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _rule(**over) -> AlertRule:
    base = dict(
        name="r",
        type=RuleType.QUEUE_BACKLOG,
        scope=ScopeType.GLOBAL,
        operator=ComparisonOperator.GT,
        threshold=10.0,
        for_seconds=0,
        severity=Severity.WARNING,
        enabled=True,
        state=RuleState.OK,
        state_since=_NOW,
    )
    return AlertRule(**{**base, **over})


# --- pure helpers ------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "op", "threshold", "expected"),
    [
        (11, ComparisonOperator.GT, 10, True),
        (10, ComparisonOperator.GT, 10, False),
        (10, ComparisonOperator.GTE, 10, True),
        (5, ComparisonOperator.LT, 10, True),
        (10, ComparisonOperator.LTE, 10, True),
    ],
)
def test_compare(value, op, threshold, expected):
    assert evaluator.compare(value, op, threshold) is expected


def test_advance_debounce_then_fire():
    rule = _rule(for_seconds=60)
    assert evaluator._advance(rule, met=True, now=_NOW) is None
    assert rule.state is RuleState.PENDING
    # not held long enough
    assert evaluator._advance(rule, met=True, now=_NOW + timedelta(seconds=30)) is None
    assert rule.state is RuleState.PENDING
    # held past for_seconds
    assert evaluator._advance(rule, met=True, now=_NOW + timedelta(seconds=61)) == "fired"
    assert rule.state is RuleState.FIRING
    # recovers
    assert evaluator._advance(rule, met=False, now=_NOW + timedelta(seconds=90)) == "resolved"
    assert rule.state is RuleState.OK


def test_advance_immediate_fire_when_for_seconds_zero():
    rule = _rule(for_seconds=0)
    assert evaluator._advance(rule, met=True, now=_NOW) == "fired"
    assert rule.state is RuleState.FIRING


def test_advance_pending_clears_without_event():
    rule = _rule(for_seconds=60)
    evaluator._advance(rule, met=True, now=_NOW)
    assert evaluator._advance(rule, met=False, now=_NOW + timedelta(seconds=10)) is None
    assert rule.state is RuleState.OK


# --- measurement per rule type -------------------------------------


async def test_measure_queue_backlog_global_and_scoped(session):
    adapter = FakeAdapter({"default": 30, "emails": 12})
    assert await evaluator.measure(session, adapter, _rule(scope=ScopeType.GLOBAL), now=_NOW) == 42
    scoped = _rule(scope=ScopeType.QUEUE, scope_value="emails")
    assert await evaluator.measure(session, adapter, scoped, now=_NOW) == 12


async def test_measure_failure_rate(session):
    for i in range(3):
        session.add(
            TaskRecord(
                id=f"ok{i}",
                name="t",
                queue="default",
                state=TaskState.SUCCESS,
                finished_at=_NOW - timedelta(seconds=60),
            )
        )
    session.add(
        TaskRecord(
            id="bad",
            name="t",
            queue="default",
            state=TaskState.FAILURE,
            finished_at=_NOW - timedelta(seconds=60),
        )
    )
    await session.flush()
    rule = _rule(type=RuleType.FAILURE_RATE, window_seconds=300, threshold=0.2)
    assert await evaluator.measure(session, FakeAdapter({}), rule, now=_NOW) == pytest.approx(0.25)


async def test_measure_worker_down(session):
    session.add(WorkerRecord(id="w1", last_heartbeat_at=_NOW - timedelta(seconds=200)))
    await session.flush()
    rule = _rule(type=RuleType.WORKER_DOWN, scope=ScopeType.WORKER, scope_value="w1")
    assert await evaluator.measure(session, FakeAdapter({}), rule, now=_NOW) == pytest.approx(200)
    # unknown worker -> 0 (can't alert on one we've never seen)
    unknown = _rule(type=RuleType.WORKER_DOWN, scope=ScopeType.WORKER, scope_value="ghost")
    assert await evaluator.measure(session, FakeAdapter({}), unknown, now=_NOW) == 0


async def test_measure_stuck_task(session):
    session.add(
        TaskRecord(
            id="slow",
            name="t",
            queue="default",
            state=TaskState.STARTED,
            started_at=_NOW - timedelta(seconds=1800),
        )
    )
    await session.flush()
    rule = _rule(type=RuleType.STUCK_TASK, threshold=600)
    assert await evaluator.measure(session, FakeAdapter({}), rule, now=_NOW) == pytest.approx(1800)


# --- full cycle ------------------------------------------------------


async def test_run_cycle_fires_and_resolves(session):
    rule = _rule(
        scope=ScopeType.QUEUE, scope_value="emails", threshold=10, for_seconds=0, name="emails"
    )
    session.add(rule)
    await session.flush()

    calls: list[tuple[str, bool]] = []

    async def dispatch(_session, _rule, _event, *, resolved):
        calls.append(("dispatch", resolved))

    async def broadcast(msg):
        calls.append(("broadcast", msg["data"]["state"] == "resolved"))

    over = FakeAdapter({"emails": 40})
    t = await evaluator.run_cycle(session, over, now=_NOW, dispatch=dispatch, broadcast=broadcast)
    assert t == [(rule.id, "fired")]
    assert rule.state is RuleState.FIRING
    events = (await session.scalars(select(AlertEvent))).all()
    assert len(events) == 1 and events[0].resolved_at is None

    drained = FakeAdapter({"emails": 0})
    t = await evaluator.run_cycle(
        session, drained, now=_NOW + timedelta(seconds=30), dispatch=dispatch, broadcast=broadcast
    )
    assert t == [(rule.id, "resolved")]
    assert rule.state is RuleState.OK
    events = (await session.scalars(select(AlertEvent))).all()
    assert events[0].resolved_at is not None
    assert calls == [
        ("dispatch", False),
        ("broadcast", False),
        ("dispatch", True),
        ("broadcast", True),
    ]


async def test_run_cycle_skips_disabled_rules(session):
    session.add(_rule(scope=ScopeType.QUEUE, scope_value="q", threshold=1, enabled=False))
    await session.flush()
    t = await evaluator.run_cycle(
        session, FakeAdapter({"q": 99}), now=_NOW, dispatch=_noop, broadcast=_noop
    )
    assert t == []


async def _noop(*a, **k):
    pass
