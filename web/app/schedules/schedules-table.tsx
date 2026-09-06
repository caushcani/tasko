'use client'

import { DataTable } from '@/lib/table/DataTable'
import { useServerTable } from '@/lib/table/useServerTable'
import { scheduleColumns } from './columns'
import { fetchSchedules } from './fetch-schedules'

export function SchedulesTable() {
  const { table, isLoading, search, setSearch, totalCount } = useServerTable({
    queryKey: 'schedules',
    fetcher: fetchSchedules,
    columns: scheduleColumns,
  })

  return (
    <DataTable
      table={table}
      totalCount={totalCount}
      search={search}
      onSearchChange={setSearch}
      isLoading={isLoading}
      searchPlaceholder="Search schedules…"
      emptyMessage="No schedules — wire TaskoScheduleSource into your Taskiq scheduler to see them here."
    />
  )
}
