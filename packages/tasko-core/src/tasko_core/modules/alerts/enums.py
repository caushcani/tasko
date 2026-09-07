from __future__ import annotations

from enum import StrEnum


class RuleType(StrEnum):
    QUEUE_BACKLOG = "queue_backlog"
    FAILURE_RATE = "failure_rate"
    WORKER_DOWN = "worker_down"
    STUCK_TASK = "stuck_task"


class ScopeType(StrEnum):
    GLOBAL = "global"  # applies fleet-wide
    QUEUE = "queue"  # scope_value = queue name
    TASK_NAME = "task_name"  # scope_value = task name
    WORKER = "worker"  # scope_value = worker id


class ComparisonOperator(StrEnum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"


class Severity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


class RuleState(StrEnum):
    OK = "ok"
    PENDING = "pending"  # condition true, not yet held for `for_seconds`
    FIRING = "firing"


class ChannelType(StrEnum):
    WEBHOOK = "webhook"
    EMAIL = "email"


#: Which scopes each rule type accepts. Enforced on create/update.
ALLOWED_SCOPES: dict[RuleType, frozenset[ScopeType]] = {
    RuleType.QUEUE_BACKLOG: frozenset({ScopeType.GLOBAL, ScopeType.QUEUE}),
    RuleType.FAILURE_RATE: frozenset({ScopeType.GLOBAL, ScopeType.QUEUE, ScopeType.TASK_NAME}),
    RuleType.WORKER_DOWN: frozenset({ScopeType.GLOBAL, ScopeType.WORKER}),
    RuleType.STUCK_TASK: frozenset(
        {ScopeType.GLOBAL, ScopeType.QUEUE, ScopeType.TASK_NAME, ScopeType.WORKER}
    ),
}

#: The unit the rule's ``threshold`` (and evaluated ``value``) is expressed in.
#: ``ratio`` is 0..1; the UI renders it as a percentage.
THRESHOLD_UNIT: dict[RuleType, str] = {
    RuleType.QUEUE_BACKLOG: "tasks",
    RuleType.FAILURE_RATE: "ratio",
    RuleType.WORKER_DOWN: "seconds",
    RuleType.STUCK_TASK: "seconds",
}

#: Rule types that measure over a trailing window (need ``window_seconds``).
WINDOWED_TYPES: frozenset[RuleType] = frozenset({RuleType.FAILURE_RATE})
