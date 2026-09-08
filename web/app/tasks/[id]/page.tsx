import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { fetchTaskGraph, fetchTaskOrNull } from '../fetch-tasks'
import { formatAbsolute, formatDuration, formatRelative } from '@/lib/format'
import { StatusBadge } from '../status-badge'
import { LineagePanel } from './lineage-panel'

interface TaskDetailPageProps {
  params: Promise<{ id: string }>
}

export default async function TaskDetailPage({ params }: TaskDetailPageProps) {
  const { id } = await params
  const [task, graph] = await Promise.all([fetchTaskOrNull(id), fetchTaskGraph(id)])
  if (!task) notFound()

  return (
    <div className="flex flex-col gap-[18px]">
      <div className="page-heading">
        <div>
          <Link
            href="/tasks"
            className="text-muted-foreground mb-2 inline-flex items-center gap-1 text-xs hover:underline"
          >
            <ArrowLeft size={14} /> Back to tasks
          </Link>
          <h1 className="font-mono">{task.name}</h1>
          <p className="text-muted-foreground text-xs">{task.id}</p>
        </div>
      </div>

      <section className="panel" style={{ padding: 20 }}>
        <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <Field label="Status">
            <StatusBadge state={task.state} />
          </Field>
          <Field label="Queue">
            <span className="queue-pill">{task.queue}</span>
          </Field>
          <Field label="Worker">{task.worker_id ?? '—'}</Field>
          <Field label="Triggered by">
            {task.parent_task_id ? (
              <Link href={`/tasks/${task.parent_task_id}`} className="font-mono text-xs hover:underline">
                {task.parent_task_id}
              </Link>
            ) : (
              '—'
            )}
          </Field>
          <Field label="Retries">{task.retries}</Field>
          <Field label="Duration">{formatDuration(task.execution_ms)}</Field>
          <Field label="Queued" title={formatAbsolute(task.queued_at)}>
            {formatRelative(task.queued_at)}
          </Field>
          <Field label="Started" title={formatAbsolute(task.started_at)}>
            {formatRelative(task.started_at)}
          </Field>
          <Field label="Finished" title={formatAbsolute(task.finished_at)}>
            {formatRelative(task.finished_at)}
          </Field>
        </dl>
      </section>

      {graph && <LineagePanel graph={graph} />}

      {task.traceback && (
        <section className="panel" style={{ padding: 20, borderColor: 'var(--destructive)' }}>
          <h2 className="text-destructive mb-2 text-sm font-semibold">Traceback</h2>
          <pre className="bg-muted overflow-x-auto rounded-md p-3 font-mono text-xs whitespace-pre-wrap">
            {task.traceback}
          </pre>
        </section>
      )}

      <div className="section-grid">
        <JsonPanel title="Arguments" value={task.args} empty="No positional arguments" />
        <JsonPanel title="Keyword arguments" value={task.kwargs} empty="No keyword arguments" />
      </div>

      {task.result !== null && <JsonPanel title="Result" value={task.result} />}
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

function JsonPanel({ title, value, empty }: { title: string; value: unknown; empty?: string }) {
  const isEmpty = Array.isArray(value)
    ? value.length === 0
    : value !== null && typeof value === 'object'
      ? Object.keys(value).length === 0
      : false

  return (
    <section className="panel" style={{ padding: 20 }}>
      <h2 className="mb-2 text-sm font-semibold">{title}</h2>
      {isEmpty && empty ? (
        <p className="text-muted-foreground text-sm">{empty}</p>
      ) : (
        <pre className="bg-muted overflow-x-auto rounded-md p-3 font-mono text-xs">
          {JSON.stringify(value, null, 2)}
        </pre>
      )}
    </section>
  )
}
