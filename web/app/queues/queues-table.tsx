'use client'

import { DataTable } from '@/lib/table/DataTable'
import { useClientTable } from '@/lib/table/useClientTable'
import { queueColumns } from './columns'
import type { QueueOut } from './types'

export function QueuesTable({ queues }: { queues: QueueOut[] }) {
  const { table, search, setSearch, totalCount } = useClientTable({
    data: queues,
    columns: queueColumns,
    matches: (queue, term) => queue.name.toLowerCase().includes(term),
  })

  return (
    <DataTable
      table={table}
      totalCount={totalCount}
      search={search}
      onSearchChange={setSearch}
      searchPlaceholder="Search queues…"
      emptyMessage="No queues — nothing has been enqueued on the broker yet."
    />
  )
}
