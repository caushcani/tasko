import { ArrowLeft, ArrowUpRight } from 'lucide-react'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { fetchTasks } from '@/app/tasks/fetch-tasks'
import { StatusBadge } from '@/app/tasks/status-badge'
import { formatAbsolute, formatDuration, formatRelative } from '@/lib/format'
import { fetchWorkerOrNull } from '../fetch-workers'

interface WorkerDetailPageProps {
  params: Promise<{ id: string }>
}

export default async function WorkerDetailPage({ params }: WorkerDetailPageProps) {
  const { id } = await params
  const worker = await fetchWorkerOrNull(id)
  if (!worker) notFound()

  const recentTasks = await fetchTasks({
    offset: 0,
    limit: 10,
    sort: [],
    search: '',
    worker_id: worker.id,
  })

  return (
    <div className="flex flex-col gap-[18px]">
      <div className="page-heading">
        <div>
          <Link
            href="/workers"
            className="text-muted-foreground mb-2 inline-flex items-center gap-1 text-xs hover:underline"
          >
            <ArrowLeft size={14} /> Back to workers
          </Link>
          <h1 className="font-mono">{worker.id}</h1>
        </div>
      </div>

      <section className="panel" style={{ padding: 20 }}>
        <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <Field label="Active tasks">{worker.active_tasks}</Field>
          <Field label="Queues">
            {worker.queues.length ? (
              <span className="inline-flex flex-wrap gap-1">
                {worker.queues.map((q) => (
                  <span className="queue-pill" key={q}>
                    {q}
                  </span>
                ))}
              </span>
            ) : (
              '—'
            )}
          </Field>
          <Field label="Last heartbeat" title={formatAbsolute(worker.last_heartbeat_at)}>
            {formatRelative(worker.last_heartbeat_at)}
          </Field>
          <Field label="First seen" title={formatAbsolute(worker.first_seen_at)}>
            {formatRelative(worker.first_seen_at)}
          </Field>
        </dl>
      </section>

      <section className="panel tasks-panel">
        <div className="panel-heading tasks-heading">
          <div>
            <h2>Recent tasks</h2>
            <p>Latest activity on this worker</p>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Task name</th>
                <th>Queue</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {recentTasks.items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="muted-cell" style={{ textAlign: 'center' }}>
                    No tasks recorded for this worker yet.
                  </td>
                </tr>
              ) : (
                recentTasks.items.map((task) => (
                  <tr key={task.id}>
                    <td>
                      <Link href={`/tasks/${task.id}`} className="task-name">
                        {task.name}
                      </Link>
                    </td>
                    <td>
                      <span className="queue-pill">{task.queue}</span>
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
        {recentTasks.total_count > recentTasks.items.length && (
          <Link href={`/tasks?worker_id=${encodeURIComponent(worker.id)}`} className="view-tasks">
            View all {recentTasks.total_count} tasks <ArrowUpRight size={14} />
          </Link>
        )}
      </section>
    </div>
  )
}

function Field({
  label,
  title,
  children,
}: {
  label: string
  title?: string
  children: React.ReactNode
}) {
  return (
    <div title={title}>
      <dt className="text-muted-foreground mb-1 text-xs tracking-wide uppercase">{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}
