'use client'

// For small, fully-loaded lists (workers, queues — a handful of rows, not
// worth a paginated/URL-synced endpoint) where sort/search happen in the
// browser over data already on hand. Returns the same {table, search,
// setSearch, totalCount, isLoading} shape as useServerTable, so both share
// <DataTable>.

import { useMemo, useState } from 'react'
import {
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'

export interface UseClientTableOptions<T> {
  data: T[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- ColumnDef's own default
  columns: ColumnDef<T, any>[]
  /** Defaults to a JSON-string substring match across the whole row. */
  matches?: (row: T, term: string) => boolean
}

export function useClientTable<T>({ data, columns, matches }: UseClientTableOptions<T>) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return data
    const test = matches ?? ((row: T) => JSON.stringify(row).toLowerCase().includes(term))
    return data.filter((row) => test(row, term))
  }, [data, search, matches])

  const table = useReactTable({
    data: filtered,
    columns,
    state: {
      sorting,
      // Static, unregistered pagination row model below means this never
      // actually slices rows — it only satisfies <DataTable>'s state shape.
      pagination: { pageIndex: 0, pageSize: Math.max(filtered.length, 1) },
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return { table, isLoading: false, search, setSearch, totalCount: filtered.length }
}
