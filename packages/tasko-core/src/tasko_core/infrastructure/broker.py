"""Lifecycle + dependency for the one active broker adapter.

The adapter class is discovered and instantiated in the app lifespan
(:mod:`tasko_core.interfaces.main`) and stashed on ``app.state.adapter``; routes
reach it through :data:`AdapterDep`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from tasko_core.adapters import BrokerAdapter


def current_adapter(request: Request) -> BrokerAdapter:
    return request.app.state.adapter


AdapterDep = Annotated[BrokerAdapter, Depends(current_adapter)]
