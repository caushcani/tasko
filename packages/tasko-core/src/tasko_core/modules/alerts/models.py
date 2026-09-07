"""Persistence for the alerting engine — rules, firing history, channels."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tasko_core.infrastructure.database.base import Base, utcnow
from tasko_core.infrastructure.database.query import ListSpec, RelationSpec
from tasko_core.modules.alerts.enums import (
    ChannelType,
    ComparisonOperator,
    RuleState,
    RuleType,
    ScopeType,
    Severity,
)


def _uuid() -> str:
    return uuid4().hex


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[RuleType] = mapped_column(Enum(RuleType), index=True)

    scope: Mapped[ScopeType] = mapped_column(Enum(ScopeType), default=ScopeType.GLOBAL)
    scope_value: Mapped[str | None] = mapped_column(String(255), default=None)

    operator: Mapped[ComparisonOperator] = mapped_column(Enum(ComparisonOperator))
    threshold: Mapped[float] = mapped_column(Float)
    #: measurement window for windowed types (failure_rate); null otherwise
    window_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    #: how long the condition must hold before the rule moves PENDING -> FIRING
    for_seconds: Mapped[int] = mapped_column(Integer, default=0)

    severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.WARNING)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # --- engine-owned, read-only over the API ---
    state: Mapped[RuleState] = mapped_column(Enum(RuleState), default=RuleState.OK, index=True)
    state_since: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_value: Mapped[float | None] = mapped_column(Float, default=None)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    rule_id: Mapped[str] = mapped_column(String(32), index=True)
    #: snapshotted from the rule at fire time (the rule may change later)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), index=True)
    summary: Mapped[str] = mapped_column(String(500))
    trigger_value: Mapped[float] = mapped_column(Float)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, index=True
    )

    # constraint-free read-only join, same trick as TaskRecord.worker
    rule: Mapped[AlertRule | None] = relationship(
        AlertRule,
        primaryjoin="foreign(AlertEvent.rule_id) == AlertRule.id",
        viewonly=True,
        lazy="noload",
    )


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[ChannelType] = mapped_column(Enum(ChannelType))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    #: webhook: {"url": ..., "headers": {...}}; email: {"to": [...]}
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    #: only notify for events at or above this severity
    min_severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.WARNING)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


ALERT_RULE_LIST_SPEC = ListSpec(
    model=AlertRule,
    sortable_fields=frozenset(
        {"name", "type", "severity", "state", "enabled", "created_at", "last_evaluated_at"}
    ),
    filterable_fields=frozenset({"type", "scope", "severity", "state", "enabled"}),
    searchable_fields=("name", "scope_value"),
    default_sort=("created_at", "desc"),
)

ALERT_EVENT_LIST_SPEC = ListSpec(
    model=AlertEvent,
    sortable_fields=frozenset({"started_at", "resolved_at", "severity"}),
    filterable_fields=frozenset({"rule_id", "severity"}),
    searchable_fields=("summary",),
    default_sort=("started_at", "desc"),
    relations={
        "rule": RelationSpec(
            attr="rule",
            model=AlertRule,
            filterable_fields=frozenset({"type"}),
        ),
    },
)
