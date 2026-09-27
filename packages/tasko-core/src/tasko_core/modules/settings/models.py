"""Persistence for runtime-editable app settings.

A single row overriding ``tasko.yaml`` defaults for the handful of things you
shouldn't need to redeploy for — an SMTP relay for alert emails, and a couple
of fleet-tuning knobs a self-hoster may want to nudge without a restart.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from tasko_core.infrastructure.database.base import Base, utcnow

#: The one row this table will ever have.
SETTINGS_ID = "singleton"


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: SETTINGS_ID)

    smtp_host: Mapped[str | None] = mapped_column(String(255), default=None)
    smtp_port: Mapped[int | None] = mapped_column(Integer, default=None)
    smtp_username: Mapped[str | None] = mapped_column(String(255), default=None)
    smtp_password: Mapped[str | None] = mapped_column(String(255), default=None)
    smtp_from: Mapped[str | None] = mapped_column(String(255), default=None)
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, default=True)

    #: null means "use the tasko.yaml default"
    worker_ttl_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    alert_eval_interval_seconds: Mapped[int | None] = mapped_column(Integer, default=None)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
