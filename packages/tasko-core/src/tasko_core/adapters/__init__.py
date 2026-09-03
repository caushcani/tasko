"""Broker adapter contract and registry."""

from tasko_core.adapters.base import BrokerAdapter, QueueStats, WorkerInfo
from tasko_core.adapters.registry import get_adapter, iter_adapters, load_adapter

__all__ = [
    "BrokerAdapter",
    "QueueStats",
    "WorkerInfo",
    "get_adapter",
    "iter_adapters",
    "load_adapter",
]
