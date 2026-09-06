import { ArrowLeft, ArrowUpRight } from 'lucide-react'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { fetchTasks } from '@/app/tasks/fetch-tasks'
import { StatusBadge } from '@/app/tasks/status-badge'
import { formatAbsolute, formatDuration, formatRelative } from '@/lib/format'
import { fetchQueueOrNull } from '../fetch-queues'

interface QueueDetailPageProps {
  params: Promise<{ name: string }>
}

export default async function QueueDetailPage({ params }: QueueDetailPageProps) {
  const { name: raw } = await params
  const name = decodeURIComponent(raw)
  const queue = await fetchQueueOrNull(name)
  if (!queue) notFound()

  const recentTasks = await fetchTasks({
    offset: 0,
    limit: 10,
    sort: [],
    search: '',
    queue: queue.name,
  })

  return (
    <div className="flex flex-col gap-[18px]">
      <div className="page-heading">
        <div>
          <Link
            href="/queues"
            className="text-muted-foreground mb-2 inline-flex items-center gap-1 text-xs hover:underline"
          >
            <ArrowLeft size={14} /> Back to queues
          </Link>
          <h1 className="font-mono">{queue.name}</h1>
        </div>
      </div>

      <section className="panel" style={{ padding: 20 }}>
        <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <Field label="Depth">{queue.depth.toLocaleString()}</Field>
          <Field label="In flight">{queue.in_flight > 0 ? queue.in_flight.toLocaleString() : '—'}</Field>
          <Field
            label="Oldest message"
            title={queue.oldest_message_at ? formatAbsolute(queue.oldest_message_at) : undefined}
          >
            {queue.oldest_message_at ? formatRelative(queue.oldest_message_at) : '—'}
          </Field>
        </dl>
      </section>

      <section className="panel tasks-panel">
        <div className="panel-heading tasks-heading">
          <div>
            <h2>Recent tasks</h2>
            <p>Latest activity on this queue</p>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Task name</th>
                <th>Worker</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {recentTasks.items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="muted-cell" style={{ textAlign: 'center' }}>
                    No tasks recorded on this queue yet.
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
                    <td className="muted-cell">{task.worker_id ?? '—'}</td>
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
          <Link href={`/tasks?queue=${encodeURIComponent(queue.name)}`} className="view-tasks">
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
