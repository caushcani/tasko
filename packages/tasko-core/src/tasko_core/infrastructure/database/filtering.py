"""WHERE-clause builders. Pure SQLAlchemy — callers pass resolved columns.

The mapping from a (possibly dotted) field *name* to a column, and the
validation against a model's declared allow-lists, lives in
:mod:`tasko_core.infrastructure.database.query`. These helpers just turn
columns + values into clause elements.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, or_


def build_filter_clauses(
    pairs: Sequence[tuple[ColumnElement[Any], Any]],
) -> list[ColumnElement[bool]]:
    """One clause per (column, value). List/tuple/set values become ``IN``."""
    clauses: list[ColumnElement[bool]] = []
    for column, value in pairs:
        if isinstance(value, (list, tuple, set)):
            clauses.append(column.in_(list(value)))
        else:
            clauses.append(column == value)
    return clauses


def build_search_clause(
    columns: Sequence[ColumnElement[Any]], term: str
) -> ColumnElement[bool] | None:
    """Case-insensitive ``OR`` of ``ILIKE '%term%'`` across every column."""
    term = term.strip()
    if not columns or not term:
        return None
    pattern = f"%{term}%"
    return or_(*(column.ilike(pattern) for column in columns))
