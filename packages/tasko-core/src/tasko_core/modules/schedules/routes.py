"""HTTP endpoints for the schedules module.

Schedule *definitions* are pushed here by ``tasko-middleware``'s
``TaskoScheduleSource`` (``POST /schedules/sync``) — one full snapshot per
source. Everything else is a read: a paginated list and a detail view, both
enriched with ``last_fired_at`` (from task history) and a computed
``next_fire_at``.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from tasko_core.infrastructure.database import SessionDep
from tasko_core.infrastructure.database.base import utcnow
from tasko_core.modules.common.pagination import ListParamsDep, PaginatedResponse
from tasko_core.modules.schedules import service
from tasko_core.modules.schedules.models import ScheduleRecord
from tasko_core.modules.schedules.schemas import (
    ScheduleOut,
    ScheduleSyncRequest,
    ScheduleSyncResult,
)

router = APIRouter(tags=["schedules"])


def _to_out(record: ScheduleRecord, *, last_fired: datetime | None, now: datetime) -> ScheduleOut:
    out = ScheduleOut.model_validate(record)
    out.last_fired_at = last_fired
    out.next_fire_at = service.next_fire_at(record, after=now, last_fired=last_fired)
    return out


@router.post("/schedules/sync", response_model=ScheduleSyncResult, status_code=202)
async def sync_schedules(payload: ScheduleSyncRequest, session: SessionDep) -> ScheduleSyncResult:
    synced, removed = await service.sync_schedules(session, payload.source, payload.schedules)
    return ScheduleSyncResult(synced=synced, removed=removed)


@router.get("/schedules", response_model=PaginatedResponse[ScheduleOut])
async def list_schedules(
    params: ListParamsDep,
    session: SessionDep,
    task_name: str | None = None,
    source: str | None = None,
) -> PaginatedResponse[ScheduleOut]:
    rows, total = await service.list_schedules(
        session, params, task_name=task_name, source=source
    )
    now = utcnow()
    fired = await service.last_fired_map(session, [r.id for r in rows])
    return PaginatedResponse[ScheduleOut](
        items=[_to_out(r, last_fired=fired.get(r.id), now=now) for r in rows],
        total_count=total,
        offset=params.offset,
        limit=params.limit,
    )


@router.get("/schedules/{schedule_id}", response_model=ScheduleOut)
async def get_schedule(schedule_id: str, session: SessionDep) -> ScheduleOut:
    record = await service.get_schedule(session, schedule_id)
    if record is None:
        raise HTTPException(status_code=404, detail="schedule not found")
    fired = await service.last_fired_map(session, [record.id])
    return _to_out(record, last_fired=fired.get(record.id), now=utcnow())
