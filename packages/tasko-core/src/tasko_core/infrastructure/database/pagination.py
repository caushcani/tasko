"""ORDER BY + total-count helpers. Pure SQLAlchemy."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


def build_order_by(
    resolved: Sequence[tuple[ColumnElement[Any], str]],
) -> list[ColumnElement[Any]]:
    """``[(column, "asc" | "desc"), ...]`` → SQLAlchemy order-by elements."""
    out: list[ColumnElement[Any]] = []
    for column, direction in resolved:
        out.append(column.desc() if direction == "desc" else column.asc())
    return out


async def total_count(session: AsyncSession, filtered: Select[Any]) -> int:
    """Row count of ``filtered`` (which must not carry ORDER BY / LIMIT yet)."""
    stmt = select(func.count()).select_from(filtered.order_by(None).subquery())
    return int(await session.scalar(stmt) or 0)
