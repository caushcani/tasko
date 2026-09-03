from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from tasko_core.adapters import QueueStats


class QueueOut(BaseModel):
    name: str
    depth: int
    in_flight: int
    oldest_message_at: datetime | None
    extra: dict[str, object]

    @classmethod
    def from_stats(cls, q: QueueStats) -> QueueOut:
        return cls(
            name=q.name,
            depth=q.depth,
            in_flight=q.in_flight,
            oldest_message_at=q.oldest_message_at,
            extra=q.extra,
        )
