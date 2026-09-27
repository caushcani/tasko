"""Request/response models for the settings module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SettingsUpdate(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_username: str | None = None
    #: write-only; empty string clears a previously-set password
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool | None = None
    worker_ttl_seconds: int | None = Field(default=None, ge=5)
    alert_eval_interval_seconds: int | None = Field(default=None, ge=5)


class SettingsOut(BaseModel):
    smtp_host: str | None
    smtp_port: int | None
    smtp_username: str | None
    #: never the password itself — just whether one is stored
    smtp_password_set: bool
    smtp_from: str | None
    smtp_use_tls: bool
    worker_ttl_seconds: int | None
    alert_eval_interval_seconds: int | None
    updated_at: datetime


class SmtpTestIn(BaseModel):
    to: str = Field(min_length=1)


class SmtpTestResult(BaseModel):
    ok: bool
    detail: str
