'use client'

import { useQuery } from '@tanstack/react-query'
import { AlertCircle, ArrowUpRight, Clock3 } from 'lucide-react'
import Link from 'next/link'
import { StatusBadge } from '@/app/tasks/status-badge'
import { fetchTasks } from '@/app/tasks/fetch-tasks'
import { formatDuration, formatRelative } from '@/lib/format'

const REFRESH_MS = 10_000

export function RecentTasks({ live }: { live: boolean }) {
  const { data } = useQuery({
    queryKey: ['tasks', 'recent'],
    queryFn: () =>
      fetchTasks({ offset: 0, limit: 6, sort: [{ id: 'updated_at', desc: true }], search: '' }),
    refetchInterval: live ? REFRESH_MS : false,
  })

  const tasks = data?.items ?? []

  return (
    <section className="panel tasks-panel">
      <div className="panel-heading tasks-heading">
        <div>
          <h2>Recent tasks</h2>
          <p>Latest activity across the fleet</p>
        </div>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Task name</th>
              <th>Queue</th>
              <th>Worker</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {tasks.length === 0 ? (
              <tr>
                <td colSpan={6} className="muted-cell" style={{ textAlign: 'center' }}>
                  No tasks recorded yet.
                </td>
              </tr>
            ) : (
              tasks.map((task) => (
                <tr key={task.id}>
                  <td>
                    <Link href={`/tasks/${task.id}`} className="task-name">
                      <span className="task-glyph">
                        {task.state === 'failure' ? <AlertCircle size={13} /> : <Clock3 size={13} />}
                      </span>
                      {task.name}
                    </Link>
                  </td>
                  <td>
                    <span className="queue-pill">{task.queue}</span>
                  </td>
                  <td>
                    {task.worker_id ? (
                      <span className="worker-cell">
                        <span className="worker-dot" />
                        {task.worker_id}
                      </span>
                    ) : (
                      <span className="muted-cell">—</span>
                    )}
                  </td>
                  <td>
                    <StatusBadge state={task.state} />
                  </td>
                  <td className="mono">{formatDuration(task.execution_ms)}</td>
                  <td className="muted-cell">
                    {formatRelative(task.started_at ?? task.queued_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <Link href="/tasks" className="view-tasks">
        View all tasks <ArrowUpRight size={14} />
      </Link>
    </section>
  )
}
