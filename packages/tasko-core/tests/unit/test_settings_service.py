"""Unit tests for the settings module — singleton get/update, resolvers."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tasko_core.infrastructure.config import Config
from tasko_core.infrastructure.database.base import Base
from tasko_core.modules.settings import service
from tasko_core.modules.settings.schemas import SettingsUpdate


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def test_get_settings_creates_singleton_row(session):
    settings = await service.get_settings(session)
    assert settings.id == "singleton"
    assert settings.smtp_host is None
    assert settings.smtp_use_tls is True

    # a second call returns the same row, not a new one
    again = await service.get_settings(session)
    assert again.id == settings.id


async def test_update_settings_partial_patch(session):
    await service.update_settings(session, SettingsUpdate(smtp_host="smtp.example.com"))
    settings = await service.update_settings(session, SettingsUpdate(smtp_port=2525))
    assert settings.smtp_host == "smtp.example.com"  # untouched by the second patch
    assert settings.smtp_port == 2525


async def test_update_settings_empty_password_clears_it(session):
    await service.update_settings(session, SettingsUpdate(smtp_password="hunter2"))
    cleared = await service.update_settings(session, SettingsUpdate(smtp_password=""))
    assert cleared.smtp_password is None


async def test_effective_worker_ttl_falls_back_to_config(session):
    config = Config.model_validate({"workers": {"ttl_seconds": 45}})
    assert await service.effective_worker_ttl(session, config) == 45

    await service.update_settings(session, SettingsUpdate(worker_ttl_seconds=90))
    assert await service.effective_worker_ttl(session, config) == 90


async def test_effective_alert_eval_interval_falls_back_to_config(session):
    config = Config.model_validate({"alerts": {"eval_interval_seconds": 20}})
    assert await service.effective_alert_eval_interval(session, config) == 20

    await service.update_settings(session, SettingsUpdate(alert_eval_interval_seconds=5))
    assert await service.effective_alert_eval_interval(session, config) == 5
