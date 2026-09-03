"""Discover ``BrokerAdapter`` implementations via entry points."""

from __future__ import annotations

from functools import cache
from importlib.metadata import entry_points

from tasko_core.adapters.base import BrokerAdapter

_GROUP = "tasko.adapters"


@cache
def _entry_point_map() -> dict[str, object]:
    return {ep.name: ep for ep in entry_points(group=_GROUP)}


def iter_adapters() -> list[str]:
    """Names of every registered adapter."""
    return sorted(_entry_point_map())


def get_adapter(name: str) -> type[BrokerAdapter]:
    """Resolve an adapter class by name without instantiating it."""
    try:
        ep = _entry_point_map()[name]
    except KeyError:
        raise LookupError(
            f"no broker adapter named {name!r}; registered: {iter_adapters()}"
        ) from None
    cls = ep.load()
    if not (isinstance(cls, type) and issubclass(cls, BrokerAdapter)):
        raise TypeError(f"entry point {name!r} did not resolve to a BrokerAdapter")
    return cls


def load_adapter(name: str, **options: object) -> BrokerAdapter:
    """Resolve and instantiate an adapter."""
    return get_adapter(name)(**options)
