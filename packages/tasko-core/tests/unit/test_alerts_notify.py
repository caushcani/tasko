"""Unit tests for notification dispatch — webhook + email channels."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tasko_core.infrastructure.database.base import Base
from tasko_core.modules.alerts import notify
from tasko_core.modules.alerts.enums import (
    ChannelType,
    ComparisonOperator,
    RuleType,
    ScopeType,
    Severity,
)
from tasko_core.modules.alerts.models import AlertEvent, AlertRule, NotificationChannel
from tasko_core.modules.settings import service as settings_service
from tasko_core.modules.settings.schemas import SettingsUpdate

_NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _rule() -> AlertRule:
    return AlertRule(
        name="Emails backlog",
        type=RuleType.QUEUE_BACKLOG,
        scope=ScopeType.GLOBAL,
        operator=ComparisonOperator.GT,
        threshold=10.0,
        severity=Severity.WARNING,
    )


def _event(rule: AlertRule) -> AlertEvent:
    return AlertEvent(
        rule_id=rule.id,
        severity=Severity.WARNING,
        summary="Queue backlog: 42 > 10",
        trigger_value=42.0,
        started_at=_NOW,
    )


async def test_dispatch_sends_webhook(session):
    rule = _rule()
    session.add(rule)
    await session.flush()
    channel = NotificationChannel(
        name="hook", type=ChannelType.WEBHOOK, config={"url": "http://example.test/hook"}
    )
    session.add(channel)
    await session.flush()

    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await notify.dispatch(session, rule, _event(rule), resolved=False, client=client)
    await client.aclose()

    assert len(calls) == 1
    assert calls[0].url == httpx.URL("http://example.test/hook")


async def test_dispatch_sends_email_via_configured_smtp(session, monkeypatch):
    await settings_service.update_settings(
        session,
        SettingsUpdate(smtp_host="smtp.example.com", smtp_from="alerts@tasko.dev"),
    )
    rule = _rule()
    session.add(rule)
    await session.flush()
    channel = NotificationChannel(
        name="mail", type=ChannelType.EMAIL, config={"to": ["oncall@example.com"]}
    )
    session.add(channel)
    await session.flush()

    sent = []

    async def fake_send(message, **kwargs):
        sent.append((message, kwargs))

    monkeypatch.setattr("tasko_core.modules.settings.smtp.aiosmtplib.send", fake_send)

    await notify.dispatch(session, rule, _event(rule), resolved=False)

    assert len(sent) == 1
    message, kwargs = sent[0]
    assert message["To"] == "oncall@example.com"
    assert kwargs["hostname"] == "smtp.example.com"


async def test_dispatch_skips_email_channel_with_no_recipients(session, monkeypatch):
    await settings_service.update_settings(
        session,
        SettingsUpdate(smtp_host="smtp.example.com", smtp_from="alerts@tasko.dev"),
    )
    rule = _rule()
    session.add(rule)
    await session.flush()
    channel = NotificationChannel(name="mail", type=ChannelType.EMAIL, config={"to": []})
    session.add(channel)
    await session.flush()

    calls = []
    monkeypatch.setattr(
        "tasko_core.modules.settings.smtp.aiosmtplib.send",
        lambda *a, **k: calls.append((a, k)),
    )

    await notify.dispatch(session, rule, _event(rule), resolved=False)
    assert calls == []
