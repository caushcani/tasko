import { ArrowLeft, ArrowUpRight } from 'lucide-react'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { fetchTasks } from '@/app/tasks/fetch-tasks'
import { StatusBadge } from '@/app/tasks/status-badge'
import { formatAbsolute, formatDuration, formatRelative, formatWhen } from '@/lib/format'
import { fetchScheduleOrNull } from '../fetch-schedules'
import { formatSchedule, scheduleKind } from '../format-schedule'

interface ScheduleDetailPageProps {
  params: Promise<{ id: string }>
}

export default async function ScheduleDetailPage({ params }: ScheduleDetailPageProps) {
  const { id: raw } = await params
  const id = decodeURIComponent(raw)
  const schedule = await fetchScheduleOrNull(id)
  if (!schedule) notFound()

  const recentTasks = await fetchTasks({
    offset: 0,
    limit: 10,
    sort: [],
    search: '',
    schedule_id: schedule.id,
  })

  const hasKwargs = Object.keys(schedule.kwargs).length > 0
  const hasArgs = schedule.args.length > 0

  return (
    <div className="flex flex-col gap-[18px]">
      <div className="page-heading">
        <div>
          <Link
            href="/schedules"
            className="text-muted-foreground mb-2 inline-flex items-center gap-1 text-xs hover:underline"
          >
            <ArrowLeft size={14} /> Back to schedules
          </Link>
          <h1 className="font-mono">{schedule.task_name}</h1>
          <p className="text-muted-foreground text-xs">{schedule.id}</p>
        </div>
      </div>

      <section className="panel" style={{ padding: 20 }}>
        <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <Field label="Cadence">
            <span className="mono">{formatSchedule(schedule)}</span>
          </Field>
          <Field label="Type">
            <span className="queue-pill">{scheduleKind(schedule)}</span>
          </Field>
          <Field
            label="Next run"
            title={schedule.next_fire_at ? formatAbsolute(schedule.next_fire_at) : undefined}
          >
            {schedule.next_fire_at ? formatWhen(schedule.next_fire_at) : '—'}
          </Field>
          <Field
            label="Last run"
            title={schedule.last_fired_at ? formatAbsolute(schedule.last_fired_at) : undefined}
          >
            {schedule.last_fired_at ? formatRelative(schedule.last_fired_at) : 'never'}
          </Field>
          {schedule.cron && (
            <Field label="Cron">
              <span className="mono">{schedule.cron}</span>
              {schedule.cron_offset ? (
                <span className="text-muted-foreground"> ({schedule.cron_offset})</span>
              ) : null}
            </Field>
          )}
          <Field label="Source">
            <span className="queue-pill">{schedule.source}</span>
          </Field>
          <Field label="First seen" title={formatAbsolute(schedule.first_seen_at)}>
            {formatRelative(schedule.first_seen_at)}
          </Field>
          <Field label="Last synced" title={formatAbsolute(schedule.last_seen_at)}>
            {formatRelative(schedule.last_seen_at)}
          </Field>
        </dl>
      </section>

      {(hasArgs || hasKwargs) && (
        <div className="section-grid">
          {hasArgs && <JsonPanel title="Arguments" value={schedule.args} />}
          {hasKwargs && <JsonPanel title="Keyword arguments" value={schedule.kwargs} />}
        </div>
      )}

      <section className="panel tasks-panel">
        <div className="panel-heading tasks-heading">
          <div>
            <h2>Recent runs</h2>
            <p>Tasks kicked by this schedule</p>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Task id</th>
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
                    No runs recorded for this schedule yet.
                  </td>
                </tr>
              ) : (
                recentTasks.items.map((task) => (
                  <tr key={task.id}>
                    <td>
                      <Link href={`/tasks/${task.id}`} className="task-name">
                        {task.id}
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
          <Link
            href={`/tasks?schedule_id=${encodeURIComponent(schedule.id)}`}
            className="view-tasks"
          >
            View all {recentTasks.total_count} runs <ArrowUpRight size={14} />
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

function JsonPanel({ title, value }: { title: string; value: unknown }) {
  return (
    <section className="panel" style={{ padding: 20 }}>
      <h2 className="mb-2 text-sm font-semibold">{title}</h2>
      <pre className="bg-muted overflow-x-auto rounded-md p-3 font-mono text-xs">
        {JSON.stringify(value, null, 2)}
      </pre>
    </section>
  )
}
