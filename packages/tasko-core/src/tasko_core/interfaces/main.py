"""FastAPI application instance, middleware, and lifespan."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tasko_core import __version__
from tasko_core.adapters import iter_adapters, load_adapter
from tasko_core.infrastructure.config import Config, load_config
from tasko_core.infrastructure.database import (
    BadListField,
    create_all,
    dispose_engine,
    init_engine,
)
from tasko_core.interfaces.api.v1 import api_router, ws_router


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config: Config = app.state.config

    init_engine(config.database.url)
    await create_all()

    adapter = load_adapter(config.broker.adapter, **config.broker.options)
    await adapter.startup()
    app.state.adapter = adapter

    try:
        yield
    finally:
        await adapter.shutdown()
        await dispose_engine()


def create_app(config: Config | None = None) -> FastAPI:
    config = config or load_config()
    app = FastAPI(title="Tasko", version=__version__, lifespan=lifespan)
    app.state.config = config

    # web/ and core run on different origins (different ports, at least in
    # dev) — the dashboard's browser-side fetches need this; SSR prefetches
    # are server-to-server and unaffected.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.include_router(ws_router)

    @app.exception_handler(BadListField)
    async def _bad_list_field(request: Request, exc: BadListField) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/healthz")
    async def healthz() -> dict[str, object]:
        return {"status": "ok", "version": __version__, "adapters": iter_adapters()}

    return app


#: Module-level ASGI app for ``uvicorn tasko_core.interfaces.main:app``.
app = create_app()


def run() -> None:
    """Console-script entrypoint: ``tasko-core``."""
    import uvicorn

    config = load_config()
    uvicorn.run(
        "tasko_core.interfaces.main:create_app",
        factory=True,
        host=config.server.host,
        port=config.server.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
