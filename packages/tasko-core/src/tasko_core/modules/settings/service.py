"""Get/update the singleton app-settings row, and resolve config overrides."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tasko_core.infrastructure.config import Config
from tasko_core.modules.settings.models import SETTINGS_ID, AppSettings
from tasko_core.modules.settings.schemas import SettingsUpdate


async def get_settings(session: AsyncSession) -> AppSettings:
    settings = await session.get(AppSettings, SETTINGS_ID)
    if settings is None:
        settings = AppSettings(id=SETTINGS_ID)
        session.add(settings)
        await session.flush()
    return settings


async def update_settings(session: AsyncSession, data: SettingsUpdate) -> AppSettings:
    settings = await get_settings(session)
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "smtp_password" and value == "":
            value = None
        setattr(settings, field, value)
    await session.flush()
    return settings


async def effective_worker_ttl(session: AsyncSession, config: Config) -> int:
    settings = await get_settings(session)
    return settings.worker_ttl_seconds or config.workers.ttl_seconds


async def effective_alert_eval_interval(session: AsyncSession, config: Config) -> int:
    settings = await get_settings(session)
    return settings.alert_eval_interval_seconds or config.alerts.eval_interval_seconds
