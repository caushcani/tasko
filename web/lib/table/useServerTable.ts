"use client"

// The bridge: URL search params <-> TanStack Table state <-> TanStack Query.
// The three `manual*` flags below are the important bit — they tell TanStack
// Table "don't sort/filter/paginate the rows yourself, the array you got is
// already the current page." Skipping them is the most common mistake with a
// server-driven TanStack Table setup: it'll silently re-sort/paginate
// client-side on top of already-paginated data.

import { useMemo } from "react"
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import {
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type PaginationState,
  type SortingState,
  type Updater,
} from "@tanstack/react-table"
import { parseAsInteger, parseAsString, useQueryState } from "nuqs"
import type { PaginatedResponse } from "@/lib/api/types"
import { parseSort, serializeSort, type ServerQueryState } from "./url-state"

export interface UseServerTableOptions<T, F extends Record<string, unknown>> {
  /** React Query cache key prefix — pass a stable string per module ("tasks"). */
  queryKey: string
  fetcher: (params: ServerQueryState & F) => Promise<PaginatedResponse<T>>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- ColumnDef's own default
  columns: ColumnDef<T, any>[]
  /** Module-specific filter values, e.g. { state, queue } — passed straight
   * through to `fetcher` and merged into the query key. */
  extraFilters?: F
  defaultLimit?: number
}

function resolveUpdater<S>(updater: Updater<S>, current: S): S {
  return typeof updater === "function" ? (updater as (old: S) => S)(current) : updater
}

export function useServerTable<T, F extends Record<string, unknown> = Record<string, never>>({
  queryKey,
  fetcher,
  columns,
  extraFilters,
  defaultLimit = 50,
}: UseServerTableOptions<T, F>) {
  const [offset, setOffset] = useQueryState("offset", parseAsInteger.withDefault(0))
  const [limit, setLimit] = useQueryState("limit", parseAsInteger.withDefault(defaultLimit))
  const [sortParam, setSortParam] = useQueryState("sort", parseAsString)
  const [search, setSearchParam] = useQueryState("q", parseAsString.withDefault(""))

  const sort = useMemo(() => parseSort(sortParam), [sortParam])
  const filters = (extraFilters ?? {}) as F
  const queryParams: ServerQueryState & F = { offset, limit, sort, search, ...filters }

  const { data, isLoading, isFetching } = useQuery({
    queryKey: [queryKey, queryParams],
    queryFn: () => fetcher(queryParams),
    placeholderData: keepPreviousData,
  })

  const pagination: PaginationState = {
    pageIndex: limit > 0 ? Math.floor(offset / limit) : 0,
    pageSize: limit,
  }
  const sorting: SortingState = sort.map((s) => ({ id: s.id, desc: s.desc }))

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
    pageCount: data ? Math.max(1, Math.ceil(data.total_count / Math.max(1, limit))) : -1,
    state: { pagination, sorting },
    onPaginationChange: (updater) => {
      const next = resolveUpdater(updater, pagination)
      void setOffset(next.pageIndex * next.pageSize)
      void setLimit(next.pageSize)
    },
    onSortingChange: (updater) => {
      const next = resolveUpdater(updater, sorting)
      void setSortParam(serializeSort(next) ?? null)
      void setOffset(0) // a new sort invalidates whatever page you were on
    },
    getCoreRowModel: getCoreRowModel(),
  })

  const setSearch = (value: string) => {
    void setSearchParam(value || null)
    void setOffset(0)
  }

  return {
    table,
    isLoading,
    isFetching,
    search,
    setSearch,
    totalCount: data?.total_count ?? 0,
  }
}
