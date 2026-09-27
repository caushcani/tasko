"""Fan a firing / resolved alert out to the configured notification channels.

Webhooks post a JSON payload directly. Email channels send through whatever
SMTP relay is configured in Settings — looked up lazily, once per dispatch
call, only if an email channel is actually targeted. Delivery is
best-effort — a channel that errors never blocks the evaluation cycle.
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasko_core.modules.alerts.enums import ChannelType, Severity
from tasko_core.modules.alerts.models import AlertEvent, AlertRule, NotificationChannel
from tasko_core.modules.settings import service as settings_service
from tasko_core.modules.settings import smtp
from tasko_core.modules.settings.models import AppSettings

logger = logging.getLogger("tasko.alerts")

_SEVERITY_RANK = {Severity.WARNING: 0, Severity.CRITICAL: 1}


def _payload(rule: AlertRule, event: AlertEvent, *, resolved: bool) -> dict:
    return {
        "event": "resolved" if resolved else "firing",
        "summary": event.summary,
        "value": event.trigger_value,
        "started_at": event.started_at.isoformat(),
        "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
        "rule": {
            "id": rule.id,
            "name": rule.name,
            "type": rule.type.value,
            "severity": rule.severity.value,
            "scope": rule.scope.value,
            "scope_value": rule.scope_value,
            "operator": rule.operator.value,
            "threshold": rule.threshold,
        },
    }


async def _send_webhook(
    client: httpx.AsyncClient, channel: NotificationChannel, payload: dict
) -> None:
    cfg = channel.config or {}
    url = cfg.get("url")
    if not url:
        return
    await client.post(url, json=payload, headers=cfg.get("headers") or {})


def _email_body(rule: AlertRule, event: AlertEvent, *, resolved: bool) -> str:
    state = "RESOLVED" if resolved else "FIRING"
    lines = [
        f"[{state}] {event.summary}",
        "",
        f"Rule: {rule.name}",
        f"Severity: {rule.severity.value}",
        f"Started: {event.started_at.isoformat()}",
    ]
    if event.resolved_at:
        lines.append(f"Resolved: {event.resolved_at.isoformat()}")
    return "\n".join(lines)


async def _send_email(
    settings: AppSettings,
    channel: NotificationChannel,
    rule: AlertRule,
    event: AlertEvent,
    *,
    resolved: bool,
) -> None:
    to = (channel.config or {}).get("to") or []
    if not to:
        return
    await smtp.send_email(
        settings,
        to=to,
        subject=f"Tasko alert — {rule.name}",
        body=_email_body(rule, event, resolved=resolved),
    )


async def dispatch(
    session: AsyncSession,
    rule: AlertRule,
    event: AlertEvent,
    *,
    resolved: bool,
    client: httpx.AsyncClient | None = None,
) -> None:
    channels = list(
        (
            await session.scalars(
                select(NotificationChannel).where(NotificationChannel.enabled.is_(True))
            )
        ).all()
    )
    targets = [
        c for c in channels if _SEVERITY_RANK[event.severity] >= _SEVERITY_RANK[c.min_severity]
    ]
    if not targets:
        return

    payload = _payload(rule, event, resolved=resolved)
    settings: AppSettings | None = None
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=5.0)
    try:
        for channel in targets:
            try:
                if channel.type is ChannelType.WEBHOOK:
                    await _send_webhook(client, channel, payload)
                else:
                    if settings is None:
                        settings = await settings_service.get_settings(session)
                    await _send_email(settings, channel, rule, event, resolved=resolved)
            except Exception:
                logger.warning("notification to channel %s failed", channel.name, exc_info=True)
    finally:
        if owns_client:
            await client.aclose()
