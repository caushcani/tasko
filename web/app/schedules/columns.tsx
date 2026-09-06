'use client'

import type { ColumnDef } from '@tanstack/react-table'
import Link from 'next/link'
import { formatAbsolute, formatRelative, formatWhen } from '@/lib/format'
import { formatSchedule } from './format-schedule'
import type { ScheduleOut } from './types'

export const scheduleColumns: ColumnDef<ScheduleOut>[] = [
  {
    accessorKey: 'task_name',
    header: 'Task',
    cell: ({ row }) => (
      <Link href={`/schedules/${encodeURIComponent(row.original.id)}`} className="task-name">
        {row.original.task_name}
      </Link>
    ),
  },
  {
    id: 'schedule',
    header: 'Schedule',
    enableSorting: false,
    cell: ({ row }) => (
      <span className="mono" title={row.original.cron ?? undefined}>
        {formatSchedule(row.original)}
      </span>
    ),
  },
  {
    accessorKey: 'next_fire_at',
    header: 'Next run',
    enableSorting: false,
    cell: ({ getValue }) => {
      const iso = getValue<string | null>()
      return (
        <span className="muted-cell" title={iso ? formatAbsolute(iso) : undefined}>
          {iso ? formatWhen(iso) : '—'}
        </span>
      )
    },
  },
  {
    accessorKey: 'last_fired_at',
    header: 'Last run',
    enableSorting: false,
    cell: ({ getValue }) => {
      const iso = getValue<string | null>()
      return (
        <span className="muted-cell" title={iso ? formatAbsolute(iso) : undefined}>
          {iso ? formatRelative(iso) : 'never'}
        </span>
      )
    },
  },
  {
    accessorKey: 'source',
    header: 'Source',
    cell: ({ getValue }) => <span className="queue-pill">{getValue<string>()}</span>,
  },
]
