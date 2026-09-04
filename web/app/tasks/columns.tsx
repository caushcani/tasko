'use client'

import type { ColumnDef } from '@tanstack/react-table'
import { AlertCircle, Clock3 } from 'lucide-react'
import Link from 'next/link'
import { formatDuration, formatRelative } from './format'
import { StatusBadge } from './status-badge'
import type { TaskOut, TaskState } from './types'

export const taskColumns: ColumnDef<TaskOut>[] = [
  {
    accessorKey: 'name',
    header: 'Task name',
    cell: ({ row }) => (
      <Link href={`/tasks/${row.original.id}`} className="task-name">
        <span className="task-glyph">
          {row.original.state === 'failure' ? <AlertCircle size={13} /> : <Clock3 size={13} />}
        </span>
        {row.original.name}
      </Link>
    ),
  },
  {
    accessorKey: 'queue',
    header: 'Queue',
    cell: ({ getValue }) => <span className="queue-pill">{getValue<string>()}</span>,
  },
  {
    accessorKey: 'worker_id',
    header: 'Worker',
    enableSorting: false,
    cell: ({ getValue }) => {
      const workerId = getValue<string | null>()
      return workerId ? (
        <span className="worker-cell">
          <span className="worker-dot" />
          {workerId}
        </span>
      ) : (
        <span className="muted-cell">—</span>
      )
    },
  },
  {
    accessorKey: 'state',
    header: 'Status',
    cell: ({ getValue }) => <StatusBadge state={getValue<TaskState>()} />,
  },
  {
    accessorKey: 'execution_ms',
    header: 'Duration',
    cell: ({ getValue }) => <span className="mono">{formatDuration(getValue<number | null>())}</span>,
  },
  {
    accessorKey: 'started_at',
    header: 'Started',
    cell: ({ row }) => (
      <span className="muted-cell">
        {formatRelative(row.original.started_at ?? row.original.queued_at)}
      </span>
    ),
  },
]
