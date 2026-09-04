'use client'

import { useQueryStates } from 'nuqs'
import { DataTable } from '@/lib/table/DataTable'
import { FilterBar } from '@/lib/table/FilterBar'
import { parserFor } from '@/lib/table/nuqs-parsers'
import { useServerTable } from '@/lib/table/useServerTable'
import { taskColumns } from './columns'
import { fetchTasks, type TaskFilters } from './fetch-tasks'
import { TASK_FILTERS } from './filters'

export function TasksTable() {
  // Same parser-per-field construction the server loader
  // (search-params.ts) uses, so the two never disagree on a value.
  const [filters, setFilters] = useQueryStates(
    Object.fromEntries(TASK_FILTERS.map((f) => [f.field, parserFor(f)])),
  )

  const { table, isLoading, search, setSearch, totalCount } = useServerTable({
    queryKey: 'tasks',
    fetcher: fetchTasks,
    columns: taskColumns,
    extraFilters: filters as TaskFilters,
  })

  return (
    <div className="flex flex-col gap-4">
      <FilterBar
        fields={TASK_FILTERS}
        value={filters}
        onChange={(field, value) => void setFilters({ [field]: value ?? null })}
      />
      <DataTable
        table={table}
        totalCount={totalCount}
        search={search}
        onSearchChange={setSearch}
        isLoading={isLoading}
        searchPlaceholder="Search tasks…"
        emptyMessage="No tasks match these filters."
      />
    </div>
  )
}
