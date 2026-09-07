"""The background evaluation loop, started from the app lifespan."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import FastAPI

from tasko_core.infrastructure.database import session_scope
from tasko_core.modules.alerts.evaluator import run_cycle

logger = logging.getLogger("tasko.alerts")


async def _loop(app: FastAPI) -> None:
    interval = app.state.config.alerts.eval_interval_seconds
    while True:
        try:
            async with session_scope() as session:
                await run_cycle(session, app.state.adapter)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("alert evaluation cycle failed")
        await asyncio.sleep(interval)


def start(app: FastAPI) -> asyncio.Task[None] | None:
    """Kick off the loop unless disabled in config. Returns the task so the
    lifespan can cancel it on shutdown."""
    if not app.state.config.alerts.enabled:
        return None
    return asyncio.create_task(_loop(app), name="tasko-alert-loop")


async def stop(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
