"""v1 router aggregator — mounts every module's routes under ``/api``."""

from fastapi import APIRouter

from tasko_core.interfaces.api.v1 import websocket
from tasko_core.modules.queues import routes as queues_routes
from tasko_core.modules.schedules import routes as schedules_routes
from tasko_core.modules.tasks import routes as tasks_routes
from tasko_core.modules.workers import routes as workers_routes

api_router = APIRouter(prefix="/api")
api_router.include_router(tasks_routes.router)
api_router.include_router(workers_routes.router)
api_router.include_router(queues_routes.router)
api_router.include_router(schedules_routes.router)

# WebSocket lives at /ws (no /api prefix).
ws_router = websocket.router

__all__ = ["api_router", "ws_router"]
