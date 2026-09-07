"""HTTP endpoints for the alerts module."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from tasko_core.infrastructure.broker import AdapterDep
from tasko_core.infrastructure.database import SessionDep
from tasko_core.infrastructure.database.base import utcnow
from tasko_core.modules.alerts import evaluator, service
from tasko_core.modules.alerts.enums import ChannelType, Severity
from tasko_core.modules.alerts.schemas import (
    AlertEventOut,
    AlertRuleIn,
    AlertRuleOut,
    AlertRuleUpdate,
    ChannelTestResult,
    NotificationChannelIn,
    NotificationChannelOut,
    NotificationChannelUpdate,
)
from tasko_core.modules.common.pagination import ListParamsDep, PaginatedResponse

router = APIRouter(tags=["alerts"], prefix="/alerts")


# --- rules -------------------------------------------------------------


@router.get("/rules", response_model=PaginatedResponse[AlertRuleOut])
async def list_rules(
    params: ListParamsDep,
    session: SessionDep,
    type: str | None = None,
    scope: str | None = None,
    severity: Severity | None = None,
    state: str | None = None,
    enabled: bool | None = None,
) -> PaginatedResponse[AlertRuleOut]:
    rows, total = await service.list_rules(
        session, params, type=type, scope=scope, severity=severity, state=state, enabled=enabled
    )
    return PaginatedResponse[AlertRuleOut](
        items=[AlertRuleOut.model_validate(r) for r in rows],
        total_count=total,
        offset=params.offset,
        limit=params.limit,
    )


@router.post("/rules", response_model=AlertRuleOut, status_code=201)
async def create_rule(payload: AlertRuleIn, session: SessionDep) -> AlertRuleOut:
    rule = await service.create_rule(session, payload)
    return AlertRuleOut.model_validate(rule)


@router.get("/rules/{rule_id}", response_model=AlertRuleOut)
async def get_rule(rule_id: str, session: SessionDep) -> AlertRuleOut:
    rule = await service.get_rule(session, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    return AlertRuleOut.model_validate(rule)


@router.patch("/rules/{rule_id}", response_model=AlertRuleOut)
async def update_rule(rule_id: str, payload: AlertRuleUpdate, session: SessionDep) -> AlertRuleOut:
    rule = await service.get_rule(session, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    rule = await service.update_rule(session, rule, payload)
    return AlertRuleOut.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, session: SessionDep) -> None:
    rule = await service.get_rule(session, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    await service.delete_rule(session, rule)


@router.post("/rules/{rule_id}/evaluate", response_model=AlertRuleOut)
async def evaluate_rule_now(rule_id: str, session: SessionDep, adapter: AdapterDep) -> AlertRuleOut:
    rule = await service.get_rule(session, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    met, value, _ = await evaluator.evaluate(session, adapter, rule, now=utcnow())
    rule.last_value = value
    rule.last_evaluated_at = utcnow()
    await session.flush()
    return AlertRuleOut.model_validate(rule)


# --- events ----------------------------------------------------------


@router.get("/events", response_model=PaginatedResponse[AlertEventOut])
async def list_events(
    params: ListParamsDep,
    session: SessionDep,
    rule_id: str | None = None,
    severity: Severity | None = None,
    active: bool | None = None,
) -> PaginatedResponse[AlertEventOut]:
    rows, total = await service.list_events(
        session, params, rule_id=rule_id, severity=severity, active=active
    )
    names = await service.rule_names(session, [r.rule_id for r in rows])
    items = []
    for row in rows:
        out = AlertEventOut.model_validate(row)
        out.rule_name = names.get(row.rule_id)
        items.append(out)
    return PaginatedResponse[AlertEventOut](
        items=items, total_count=total, offset=params.offset, limit=params.limit
    )


# --- channels ------------------------------------------------------


@router.get("/channels", response_model=list[NotificationChannelOut])
async def list_channels(session: SessionDep) -> list[NotificationChannelOut]:
    return [NotificationChannelOut.model_validate(c) for c in await service.list_channels(session)]


@router.post("/channels", response_model=NotificationChannelOut, status_code=201)
async def create_channel(
    payload: NotificationChannelIn, session: SessionDep
) -> NotificationChannelOut:
    channel = await service.create_channel(session, payload)
    return NotificationChannelOut.model_validate(channel)


@router.patch("/channels/{channel_id}", response_model=NotificationChannelOut)
async def update_channel(
    channel_id: str, payload: NotificationChannelUpdate, session: SessionDep
) -> NotificationChannelOut:
    channel = await service.get_channel(session, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel not found")
    channel = await service.update_channel(session, channel, payload)
    return NotificationChannelOut.model_validate(channel)


@router.delete("/channels/{channel_id}", status_code=204)
async def delete_channel(channel_id: str, session: SessionDep) -> None:
    channel = await service.get_channel(session, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel not found")
    await service.delete_channel(session, channel)


@router.post("/channels/{channel_id}/test", response_model=ChannelTestResult)
async def test_channel(channel_id: str, session: SessionDep) -> ChannelTestResult:
    channel = await service.get_channel(session, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel not found")
    if channel.type is not ChannelType.WEBHOOK:
        return ChannelTestResult(
            ok=False, detail=f"{channel.type.value} delivery isn't wired up yet"
        )

    payload = {
        "event": "test",
        "summary": "Tasko test notification — this channel is reachable.",
        "rule": {"name": "Test", "severity": Severity.WARNING.value},
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                channel.config.get("url"),
                json=payload,
                headers=channel.config.get("headers") or {},
            )
        return ChannelTestResult(ok=resp.is_success, detail=f"HTTP {resp.status_code}")
    except httpx.HTTPError as exc:
        return ChannelTestResult(ok=False, detail=str(exc) or exc.__class__.__name__)
