'use client'

import type { ColumnDef } from '@tanstack/react-table'
import Link from 'next/link'
import { formatAbsolute, formatRelative } from '@/lib/format'
import type { WorkerOut } from './types'

export const workerColumns: ColumnDef<WorkerOut>[] = [
  {
    accessorKey: 'id',
    header: 'Worker',
    cell: ({ getValue }) => {
      const id = getValue<string>()
      return (
        <Link href={`/workers/${encodeURIComponent(id)}`} className="worker-cell">
          <span className="worker-dot" />
          {id}
        </Link>
      )
    },
  },
  {
    accessorKey: 'queues',
    header: 'Queues',
    enableSorting: false,
    cell: ({ getValue }) => {
      const queues = getValue<string[]>()
      return queues.length ? (
        <span className="inline-flex flex-wrap gap-1">
          {queues.map((q) => (
            <span className="queue-pill" key={q}>
              {q}
            </span>
          ))}
        </span>
      ) : (
        <span className="muted-cell">—</span>
      )
    },
  },
  {
    accessorKey: 'active_tasks',
    header: 'Active tasks',
    cell: ({ getValue }) => <span className="mono">{getValue<number>()}</span>,
  },
  {
    accessorKey: 'last_heartbeat_at',
    header: 'Last heartbeat',
    cell: ({ getValue }) => {
      const iso = getValue<string>()
      return (
        <span className="muted-cell" title={formatAbsolute(iso)}>
          {formatRelative(iso)}
        </span>
      )
    },
  },
  {
    accessorKey: 'first_seen_at',
    header: 'First seen',
    cell: ({ getValue }) => {
      const iso = getValue<string>()
      return (
        <span className="muted-cell" title={formatAbsolute(iso)}>
          {formatRelative(iso)}
        </span>
      )
    },
  },
]
