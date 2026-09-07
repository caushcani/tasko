"""CRUD + list helpers for alert rules, events, and notification channels."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasko_core.infrastructure.database import run_list_query
from tasko_core.infrastructure.database.base import utcnow
from tasko_core.modules.alerts.enums import RuleState, Severity
from tasko_core.modules.alerts.models import (
    ALERT_EVENT_LIST_SPEC,
    ALERT_RULE_LIST_SPEC,
    AlertEvent,
    AlertRule,
    NotificationChannel,
)
from tasko_core.modules.alerts.schemas import (
    AlertRuleIn,
    AlertRuleUpdate,
    NotificationChannelIn,
    NotificationChannelUpdate,
)
from tasko_core.modules.common.pagination import ListParams

# --- rules -------------------------------------------------------------


async def list_rules(
    session: AsyncSession, params: ListParams, **filters: object
) -> tuple[list[AlertRule], int]:
    clean = {k: v for k, v in filters.items() if v is not None}
    return await run_list_query(
        session,
        ALERT_RULE_LIST_SPEC,
        offset=params.offset,
        limit=params.limit,
        sort_columns=params.sort_columns,
        sort_orders=params.sort_orders,
        search=params.search,
        filters=clean,
    )


async def get_rule(session: AsyncSession, rule_id: str) -> AlertRule | None:
    return await session.get(AlertRule, rule_id)


async def create_rule(session: AsyncSession, data: AlertRuleIn) -> AlertRule:
    rule = AlertRule(**data.model_dump())
    session.add(rule)
    await session.flush()
    return rule


async def update_rule(session: AsyncSession, rule: AlertRule, data: AlertRuleUpdate) -> AlertRule:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    # a config change re-arms the rule — don't leave it stuck FIRING on stale terms
    rule.state = RuleState.OK
    rule.state_since = utcnow()
    await session.flush()
    return rule


async def delete_rule(session: AsyncSession, rule: AlertRule) -> None:
    await session.execute(AlertEvent.__table__.delete().where(AlertEvent.rule_id == rule.id))
    await session.delete(rule)
    await session.flush()


# --- events ----------------------------------------------------------


async def list_events(
    session: AsyncSession,
    params: ListParams,
    *,
    rule_id: str | None = None,
    severity: Severity | None = None,
    active: bool | None = None,
) -> tuple[list[AlertEvent], int]:
    filters = {k: v for k, v in {"rule_id": rule_id, "severity": severity}.items() if v is not None}
    extra = []
    if active is True:
        extra = [AlertEvent.resolved_at.is_(None)]
    elif active is False:
        extra = [AlertEvent.resolved_at.is_not(None)]
    return await run_list_query(
        session,
        ALERT_EVENT_LIST_SPEC,
        offset=params.offset,
        limit=params.limit,
        sort_columns=params.sort_columns,
        sort_orders=params.sort_orders,
        search=params.search,
        filters=filters,
        extra_where=extra,
    )


async def rule_names(session: AsyncSession, rule_ids: list[str]) -> dict[str, str]:
    if not rule_ids:
        return {}
    rows = await session.execute(
        select(AlertRule.id, AlertRule.name).where(AlertRule.id.in_(rule_ids))
    )
    return {rid: name for rid, name in rows}


# --- channels ------------------------------------------------------


async def list_channels(session: AsyncSession) -> list[NotificationChannel]:
    return list(
        (
            await session.scalars(
                select(NotificationChannel).order_by(NotificationChannel.created_at.desc())
            )
        ).all()
    )


async def get_channel(session: AsyncSession, channel_id: str) -> NotificationChannel | None:
    return await session.get(NotificationChannel, channel_id)


async def create_channel(session: AsyncSession, data: NotificationChannelIn) -> NotificationChannel:
    channel = NotificationChannel(**data.model_dump())
    session.add(channel)
    await session.flush()
    return channel


async def update_channel(
    session: AsyncSession, channel: NotificationChannel, data: NotificationChannelUpdate
) -> NotificationChannel:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(channel, field, value)
    await session.flush()
    return channel


async def delete_channel(session: AsyncSession, channel: NotificationChannel) -> None:
    await session.delete(channel)
    await session.flush()
