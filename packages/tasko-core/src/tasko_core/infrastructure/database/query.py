"""``ListSpec`` / ``RelationSpec`` and :func:`run_list_query`.

A model declares once — next to itself — what its list endpoint allows
(sortable / filterable / searchable fields, and any to-one relations whose
columns are reachable via dotted names like ``worker.last_heartbeat_at``).
Every module's ``service.py`` then builds a small dict of explicit filter
kwargs and makes one call to :func:`run_list_query`.

Scope, on purpose:

* **To-one joins only.** A to-many relation joined for filtering would
  multiply rows — that's an aggregation problem, handled per-module.
* **No generic ``field__op=value`` DSL.** Filter keys are validated against
  ``filterable_fields``; the values come from typed FastAPI query params.
* **Two queries per call** (count + page). Fine at self-hosted scale.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tasko_core.infrastructure.database.filtering import (
    build_filter_clauses,
    build_search_clause,
)
from tasko_core.infrastructure.database.pagination import build_order_by, total_count


class BadListField(ValueError):
    """A field name in ``sort`` / a filter key isn't on the model's allow-list."""


@dataclass(frozen=True)
class RelationSpec:
    #: relationship attribute on the parent model (used for the JOIN)
    attr: str
    #: the related model class (columns resolved off this)
    model: type
    sortable_fields: frozenset[str] = frozenset()
    filterable_fields: frozenset[str] = frozenset()
    searchable_fields: tuple[str, ...] = ()
    #: add ``selectinload`` so the response can include related data
    eager: bool = False


@dataclass(frozen=True)
class ListSpec:
    model: type
    sortable_fields: frozenset[str] = frozenset()
    filterable_fields: frozenset[str] = frozenset()
    searchable_fields: tuple[str, ...] = ()
    relations: Mapping[str, RelationSpec] = field(default_factory=dict)
    #: applied when the request supplies no ``sort``
    default_sort: tuple[str, str] | None = None

    # --- field resolution -------------------------------------------------

    def _column(self, name: str) -> tuple[ColumnElement[Any], str | None]:
        """``"name"`` → (col, None); ``"worker.hostname"`` → (col, "worker")."""
        if "." not in name:
            return getattr(self.model, name), None
        rel_name, _, attr = name.partition(".")
        rel = self.relations.get(rel_name)
        if rel is None:
            raise BadListField(f"unknown relation {rel_name!r}")
        return getattr(rel.model, attr), rel_name

    def resolve(self, name: str, kind: str) -> tuple[ColumnElement[Any], str | None]:
        """Validate ``name`` against the ``{kind}able_fields`` allow-list."""
        allowed_attr = f"{kind}able_fields"
        if "." in name:
            rel_name, _, attr = name.partition(".")
            rel = self.relations.get(rel_name)
            allowed = getattr(rel, allowed_attr, frozenset()) if rel else frozenset()
            plain = attr
        else:
            rel_name = None
            allowed = getattr(self, allowed_attr)
            plain = name
        if plain not in allowed:
            raise BadListField(f"cannot {kind} by {name!r}")
        column, rel_name = self._column(name)
        return column, rel_name

    def search_columns(self) -> list[tuple[ColumnElement[Any], str | None]]:
        cols: list[tuple[ColumnElement[Any], str | None]] = [
            (getattr(self.model, f), None) for f in self.searchable_fields
        ]
        for rel_name, rel in self.relations.items():
            cols.extend((getattr(rel.model, f), rel_name) for f in rel.searchable_fields)
        return cols


async def run_list_query(
    session: AsyncSession,
    spec: ListSpec,
    *,
    offset: int,
    limit: int,
    sort_columns: Sequence[str] = (),
    sort_orders: Sequence[str] = (),
    search: str | None = None,
    filters: Mapping[str, Any] | None = None,
) -> tuple[list[Any], int]:
    """Return ``(page_rows, total_count)`` for ``spec`` under the given params."""
    filters = filters or {}

    resolved_filters: list[tuple[ColumnElement[Any], Any]] = []
    resolved_sort: list[tuple[ColumnElement[Any], str]] = []
    needed_joins: set[str] = set()

    for key, value in filters.items():
        column, rel_name = spec.resolve(key, "filter")
        resolved_filters.append((column, value))
        if rel_name:
            needed_joins.add(rel_name)

    for name, order in zip(sort_columns, sort_orders, strict=True):
        column, rel_name = spec.resolve(name, "sort")
        resolved_sort.append((column, order))
        if rel_name:
            needed_joins.add(rel_name)

    search_cols: list[ColumnElement[Any]] = []
    if search and search.strip():
        for column, rel_name in spec.search_columns():
            search_cols.append(column)
            if rel_name:
                needed_joins.add(rel_name)

    stmt = select(spec.model)
    for rel_name in needed_joins:
        # LEFT join: sorting/searching a relation must never drop rows that
        # simply lack it (a task with no worker still exists). An explicit
        # `worker.x == v` filter still restricts correctly through the outer join.
        stmt = stmt.outerjoin(getattr(spec.model, spec.relations[rel_name].attr))

    where = build_filter_clauses(resolved_filters)
    if search_cols:
        clause = build_search_clause(search_cols, search or "")
        if clause is not None:
            where.append(clause)
    if where:
        stmt = stmt.where(*where)

    total = await total_count(session, stmt)

    order_by = build_order_by(resolved_sort)
    if not order_by and spec.default_sort:
        name, direction = spec.default_sort
        column, _ = spec._column(name)
        order_by = build_order_by([(column, direction)])
    if order_by:
        stmt = stmt.order_by(*order_by)

    for rel in spec.relations.values():
        if rel.eager:
            stmt = stmt.options(selectinload(getattr(spec.model, rel.attr)))

    stmt = stmt.offset(offset).limit(limit)
    rows = list((await session.scalars(stmt)).unique().all())
    return rows, total
