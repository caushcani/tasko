"""The rule engine: measure each rule's current value, compare to its
threshold, and walk the OK -> PENDING -> FIRING state machine.

Runs every ``config.alerts.eval_interval_seconds`` from a background task (see
:mod:`tasko_core.modules.alerts.loop`). Deliberately query-light — a handful of
COUNT / MIN / MAX per rule at self-hosted scale.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tasko_core.adapters import BrokerAdapter
from tasko_core.infrastructure.database.base import utcnow
from tasko_core.infrastructure.realtime import hub
from tasko_core.modules.alerts import notify
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

logger = logging.getLogger("tasko.alerts")

_TERMINAL = (TaskState.SUCCESS, TaskState.FAILURE)
_OP_SYMBOL = {
    ComparisonOperator.GT: ">",
    ComparisonOperator.GTE: "≥",
    ComparisonOperator.LT: "<",
    ComparisonOperator.LTE: "≤",
}
_RULE_LABEL = {
    RuleType.QUEUE_BACKLOG: "Queue backlog",
    RuleType.FAILURE_RATE: "Failure rate",
    RuleType.WORKER_DOWN: "Worker silent",
    RuleType.STUCK_TASK: "Stuck task",
}

Dispatcher = Callable[..., Awaitable[Any]]
Broadcaster = Callable[[dict], Awaitable[Any]]


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def compare(value: float, op: ComparisonOperator, threshold: float) -> bool:
    if op is ComparisonOperator.GT:
        return value > threshold
    if op is ComparisonOperator.GTE:
        return value >= threshold
    if op is ComparisonOperator.LT:
        return value < threshold
    return value <= threshold


def _fmt(value: float, unit: str) -> str:
    if unit == "ratio":
        return f"{value * 100:.1f}%"
    if unit == "seconds":
        secs = int(value)
        if secs >= 3600:
            return f"{secs // 3600}h {(secs % 3600) // 60}m"
        if secs >= 60:
            return f"{secs // 60}m {secs % 60}s"
        return f"{secs}s"
    return str(int(round(value)))


def render_summary(rule: AlertRule, value: float) -> str:
    from tasko_core.modules.alerts.enums import THRESHOLD_UNIT

    unit = THRESHOLD_UNIT[rule.type]
    scope = f" ({rule.scope_value})" if rule.scope is not ScopeType.GLOBAL else ""
    return (
        f"{_RULE_LABEL[rule.type]}{scope}: {_fmt(value, unit)} "
        f"{_OP_SYMBOL[rule.operator]} {_fmt(rule.threshold, unit)}"
    )


# --- measurement ---------------------------------------------------------


def _task_scope_clauses(rule: AlertRule) -> list[ColumnElement[bool]]:
    if rule.scope is ScopeType.QUEUE:
        return [TaskRecord.queue == rule.scope_value]
    if rule.scope is ScopeType.TASK_NAME:
        return [TaskRecord.name == rule.scope_value]
    if rule.scope is ScopeType.WORKER:
        return [TaskRecord.worker_id == rule.scope_value]
    return []


async def measure(
    session: AsyncSession, adapter: BrokerAdapter, rule: AlertRule, *, now: datetime
) -> float:
    if rule.type is RuleType.QUEUE_BACKLOG:
        if rule.scope is ScopeType.QUEUE:
            stats = await adapter.get_queue(rule.scope_value or "")
            return float(stats.depth) if stats else 0.0
        return float(sum(q.depth for q in await adapter.list_queues()))

    if rule.type is RuleType.FAILURE_RATE:
        start = now - timedelta(seconds=rule.window_seconds or 300)
        states = (
            (
                await session.execute(
                    select(TaskRecord.state)
                    .where(
                        TaskRecord.finished_at >= start,
                        TaskRecord.finished_at <= now,
                        TaskRecord.state.in_(_TERMINAL),
                        *_task_scope_clauses(rule),
                    )
                    .limit(200_000)
                )
            )
            .scalars()
            .all()
        )
        if not states:
            return 0.0
        failures = sum(1 for s in states if s == TaskState.FAILURE)
        return failures / len(states)

    if rule.type is RuleType.WORKER_DOWN:
        if rule.scope is ScopeType.WORKER:
            worker = await session.get(WorkerRecord, rule.scope_value)
            if worker is None:
                return 0.0
            return max(0.0, (now - _aware(worker.last_heartbeat_at)).total_seconds())
        oldest = await session.scalar(select(func.min(WorkerRecord.last_heartbeat_at)))
        if oldest is None:
            return 0.0
        return max(0.0, (now - _aware(oldest)).total_seconds())

    # STUCK_TASK
    oldest_started = await session.scalar(
        select(func.min(TaskRecord.started_at)).where(
            TaskRecord.state == TaskState.STARTED,
            TaskRecord.started_at.is_not(None),
            *_task_scope_clauses(rule),
        )
    )
    if oldest_started is None:
        return 0.0
    return max(0.0, (now - _aware(oldest_started)).total_seconds())


async def evaluate(
    session: AsyncSession, adapter: BrokerAdapter, rule: AlertRule, *, now: datetime
) -> tuple[bool, float, str]:
    value = await measure(session, adapter, rule, now=now)
    return compare(value, rule.operator, rule.threshold), value, render_summary(rule, value)


# --- state machine ------------------------------------------------------


def _advance(rule: AlertRule, met: bool, now: datetime) -> str | None:
    """Mutate ``rule.state`` / ``state_since``; return 'fired' | 'resolved' | None."""
    if met:
        if rule.state is RuleState.OK:
            rule.state = RuleState.PENDING
            rule.state_since = now
        if rule.state is RuleState.PENDING:
            held = (now - (_aware(rule.state_since) or now)).total_seconds()
            if held >= rule.for_seconds:
                rule.state = RuleState.FIRING
                rule.state_since = now
                return "fired"
        return None

    if rule.state is RuleState.FIRING:
        rule.state = RuleState.OK
        rule.state_since = now
        return "resolved"
    if rule.state is RuleState.PENDING:
        rule.state = RuleState.OK
        rule.state_since = now
    return None


async def _open_event(session: AsyncSession, rule_id: str) -> AlertEvent | None:
    return await session.scalar(
        select(AlertEvent)
        .where(AlertEvent.rule_id == rule_id, AlertEvent.resolved_at.is_(None))
        .order_by(AlertEvent.started_at.desc())
    )


async def _safe(fn: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> None:
    with contextlib.suppress(Exception):
        await fn(*args, **kwargs)


def _broadcast_payload(rule: AlertRule, event: AlertEvent, *, resolved: bool) -> dict:
    return {
        "type": "alert",
        "data": {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "severity": event.severity.value,
            "state": "resolved" if resolved else "firing",
            "summary": event.summary,
            "value": event.trigger_value,
        },
    }


async def run_cycle(
    session: AsyncSession,
    adapter: BrokerAdapter,
    *,
    now: datetime | None = None,
    dispatch: Dispatcher = notify.dispatch,
    broadcast: Broadcaster = hub.broadcast,
) -> list[tuple[str, str]]:
    """Evaluate every enabled rule once. Returns the list of
    ``(rule_id, "fired" | "resolved")`` transitions that happened."""
    now = now or utcnow()
    rules = list(
        (await session.scalars(select(AlertRule).where(AlertRule.enabled.is_(True)))).all()
    )
    transitions: list[tuple[str, str]] = []

    for rule in rules:
        try:
            met, value, summary = await evaluate(session, adapter, rule, now=now)
        except Exception:
            logger.exception("evaluating rule %s (%s) failed", rule.id, rule.name)
            continue

        rule.last_value = value
        rule.last_evaluated_at = now
        change = _advance(rule, met, now)

        if change == "fired":
            event = AlertEvent(
                rule_id=rule.id,
                severity=rule.severity,
                summary=summary,
                trigger_value=value,
                started_at=now,
            )
            session.add(event)
            await session.flush()
            await _safe(dispatch, session, rule, event, resolved=False)
            await _safe(broadcast, _broadcast_payload(rule, event, resolved=False))
            transitions.append((rule.id, "fired"))
        elif change == "resolved":
            event = await _open_event(session, rule.id)
            if event is not None:
                event.resolved_at = now
                await session.flush()
                await _safe(dispatch, session, rule, event, resolved=True)
                await _safe(broadcast, _broadcast_payload(rule, event, resolved=True))
            transitions.append((rule.id, "resolved"))

    await session.flush()
    return transitions


def active_severity(rules: list[AlertRule]) -> Severity | None:
    firing = [r for r in rules if r.state is RuleState.FIRING]
    if not firing:
        return None
    return (
        Severity.CRITICAL
        if any(r.severity is Severity.CRITICAL for r in firing)
        else Severity.WARNING
    )
