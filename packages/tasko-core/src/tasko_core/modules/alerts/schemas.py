"""Request/response models for the alerts module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, computed_field, model_validator

from tasko_core.modules.alerts.enums import (
    ALLOWED_SCOPES,
    THRESHOLD_UNIT,
    WINDOWED_TYPES,
    ChannelType,
    ComparisonOperator,
    RuleState,
    RuleType,
    ScopeType,
    Severity,
)


class AlertRuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: RuleType
    scope: ScopeType = ScopeType.GLOBAL
    scope_value: str | None = None
    operator: ComparisonOperator = ComparisonOperator.GT
    threshold: float
    window_seconds: int | None = Field(default=None, ge=30)
    for_seconds: int = Field(default=0, ge=0)
    severity: Severity = Severity.WARNING
    enabled: bool = True

    @model_validator(mode="after")
    def _check(self) -> AlertRuleIn:
        if self.scope not in ALLOWED_SCOPES[self.type]:
            allowed = ", ".join(sorted(s.value for s in ALLOWED_SCOPES[self.type]))
            raise ValueError(
                f"{self.type.value} can't use scope {self.scope.value} (allowed: {allowed})"
            )
        if self.scope is not ScopeType.GLOBAL and not self.scope_value:
            raise ValueError(f"scope_value is required when scope is {self.scope.value}")
        if self.type in WINDOWED_TYPES and self.window_seconds is None:
            raise ValueError(f"{self.type.value} rules need window_seconds")
        if THRESHOLD_UNIT[self.type] == "ratio" and not 0 <= self.threshold <= 1:
            raise ValueError("threshold for a rate rule must be between 0 and 1")
        return self


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    threshold: float | None = None
    window_seconds: int | None = Field(default=None, ge=30)
    for_seconds: int | None = Field(default=None, ge=0)
    operator: ComparisonOperator | None = None
    severity: Severity | None = None
    enabled: bool | None = None


class AlertRuleOut(BaseModel):
    id: str
    name: str
    type: RuleType
    scope: ScopeType
    scope_value: str | None
    operator: ComparisonOperator
    threshold: float
    window_seconds: int | None
    for_seconds: int
    severity: Severity
    enabled: bool
    state: RuleState
    state_since: datetime
    last_value: float | None
    last_evaluated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def threshold_unit(self) -> str:
        return THRESHOLD_UNIT[self.type]


class AlertEventOut(BaseModel):
    id: str
    rule_id: str
    rule_name: str | None = None
    severity: Severity
    summary: str
    trigger_value: float
    started_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class NotificationChannelIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: ChannelType
    enabled: bool = True
    config: dict = Field(default_factory=dict)
    min_severity: Severity = Severity.WARNING

    @model_validator(mode="after")
    def _check(self) -> NotificationChannelIn:
        if self.type is ChannelType.WEBHOOK and not self.config.get("url"):
            raise ValueError("webhook channel needs config.url")
        if self.type is ChannelType.EMAIL and not self.config.get("to"):
            raise ValueError("email channel needs config.to")
        return self


class NotificationChannelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    enabled: bool | None = None
    config: dict | None = None
    min_severity: Severity | None = None


class NotificationChannelOut(BaseModel):
    id: str
    name: str
    type: ChannelType
    enabled: bool
    config: dict
    min_severity: Severity
    created_at: datetime

    model_config = {"from_attributes": True}


class ChannelTestResult(BaseModel):
    ok: bool
    detail: str
