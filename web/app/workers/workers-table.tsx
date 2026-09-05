'use client'

import { DataTable } from '@/lib/table/DataTable'
import { useServerTable } from '@/lib/table/useServerTable'
import { workerColumns } from './columns'
import { fetchWorkers } from './fetch-workers'

export function WorkersTable() {
  const { table, isLoading, search, setSearch, totalCount } = useServerTable({
    queryKey: 'workers',
    fetcher: fetchWorkers,
    columns: workerColumns,
  })

  return (
    <DataTable
      table={table}
      totalCount={totalCount}
      search={search}
      onSearchChange={setSearch}
      isLoading={isLoading}
      searchPlaceholder="Search workers…"
      emptyMessage="No workers have reported a heartbeat recently."
    />
  )
}
