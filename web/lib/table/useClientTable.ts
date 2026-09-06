'use client'

// For small, fully-loaded lists (workers, queues — a handful of rows, not
// worth a paginated/URL-synced endpoint) where sort/search happen in the
// browser over data already on hand. Returns the same {table, search,
// setSearch, totalCount, isLoading} shape as useServerTable, so both share
// <DataTable>.
//
// Uses TanStack's own `globalFilter` state rather than pre-filtering the
// `data` array ourselves: a `.filter()` produces a new array reference every
// render, and feeding an unstable `data` into useReactTable triggers an
// infinite render loop. `data` here is passed straight through untouched.

import { useState } from 'react'
import {
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'

export interface UseClientTableOptions<T> {
  data: T[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- ColumnDef's own default
  columns: ColumnDef<T, any>[]
  /** True if `row` matches the trimmed, lowercased `term`. Defaults to a
   * JSON-string substring match across the whole row. */
  matches?: (row: T, term: string) => boolean
}

export function useClientTable<T>({ data, columns, matches }: UseClientTableOptions<T>) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [search, setSearch] = useState('')

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter: search },
    onSortingChange: setSorting,
    onGlobalFilterChange: setSearch,
    globalFilterFn: (row, _columnId, term) => {
      const t = String(term).trim().toLowerCase()
      if (!t) return true
      return matches
        ? matches(row.original, t)
        : JSON.stringify(row.original).toLowerCase().includes(t)
    },
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return {
    table,
    isLoading: false,
    search,
    setSearch,
    totalCount: table.getFilteredRowModel().rows.length,
  }
}
