"""HTTP endpoints for the stats module — read-only aggregates for Overview."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from tasko_core.infrastructure.database import SessionDep
from tasko_core.modules.stats import service
from tasko_core.modules.stats.schemas import OverviewOut, ThroughputOut

router = APIRouter(tags=["stats"], prefix="/stats")


@router.get("/overview", response_model=OverviewOut)
async def overview(session: SessionDep, request: Request) -> OverviewOut:
    ttl = request.app.state.config.workers.ttl_seconds
    return await service.overview(session, ttl_seconds=ttl)


@router.get("/throughput", response_model=ThroughputOut)
async def throughput(
    session: SessionDep,
    window: str = Query("24h"),
) -> ThroughputOut:
    if window not in service.WINDOWS:
        raise HTTPException(
            status_code=422, detail=f"window must be one of {sorted(service.WINDOWS)}"
        )
    return await service.throughput(session, window)
