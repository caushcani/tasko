'use client'

import type { ColumnDef } from '@tanstack/react-table'
import Link from 'next/link'
import { formatAbsolute, formatRelative } from '@/lib/format'
import type { QueueOut } from './types'

export const queueColumns: ColumnDef<QueueOut>[] = [
  {
    accessorKey: 'name',
    header: 'Queue',
    cell: ({ getValue }) => {
      const name = getValue<string>()
      return (
        <Link href={`/queues/${encodeURIComponent(name)}`} className="queue-pill">
          {name}
        </Link>
      )
    },
  },
  {
    accessorKey: 'depth',
    header: 'Depth',
    cell: ({ getValue }) => <span className="mono">{getValue<number>().toLocaleString()}</span>,
  },
  {
    accessorKey: 'in_flight',
    header: 'In flight',
    cell: ({ getValue }) => {
      const n = getValue<number>()
      return <span className="mono">{n > 0 ? n.toLocaleString() : '—'}</span>
    },
  },
  {
    accessorKey: 'oldest_message_at',
    header: 'Oldest message',
    cell: ({ getValue }) => {
      const iso = getValue<string | null>()
      return (
        <span className="muted-cell" title={iso ? formatAbsolute(iso) : undefined}>
          {iso ? formatRelative(iso) : '—'}
        </span>
      )
    },
  },
]
