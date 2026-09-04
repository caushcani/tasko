"""The FastAPI-facing shapes every list endpoint shares.

``list_params`` parses the common query string; ``PaginatedResponse[T]`` is the
common envelope. The SQL side of listing lives in
:mod:`tasko_core.infrastructure.database.query`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel

T = TypeVar("T")


@dataclass
class ListParams:
    offset: int = 0
    limit: int = 50
    search: str | None = None
    sort_columns: list[str] = field(default_factory=list)
    sort_orders: list[str] = field(default_factory=list)


def _parse_sort(sort: str | None) -> tuple[list[str], list[str]]:
    columns: list[str] = []
    orders: list[str] = []
    for token in (sort or "").split(","):
        token = token.strip()
        if not token:
            continue
        if token.startswith("-"):
            columns.append(token[1:])
            orders.append("desc")
        else:
            columns.append(token.lstrip("+"))
            orders.append("asc")
    return columns, orders


def list_params(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort: str | None = Query(
        None,
        description="comma-separated fields, '-' prefix for descending, e.g. '-updated_at,name'",
    ),
    q: str | None = Query(None, description="free-text search"),
) -> ListParams:
    columns, orders = _parse_sort(sort)
    term = q.strip() if q and q.strip() else None
    return ListParams(
        offset=offset, limit=limit, search=term, sort_columns=columns, sort_orders=orders
    )


ListParamsDep = Annotated[ListParams, Depends(list_params)]


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total_count: int
    offset: int
    limit: int
