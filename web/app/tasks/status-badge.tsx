// No "use client" — pure presentational, renders fine from a server
// component (the detail page) as well as the client-side table (columns.tsx).

import { AlertCircle, CheckCircle2, Clock3, Activity as RunningIcon, XCircle } from 'lucide-react'
import type { TaskState } from './types'

const STATE_META: Record<TaskState, { label: string; badge: string; icon: typeof CheckCircle2 }> = {
  success: { label: 'Success', badge: 'status-success', icon: CheckCircle2 },
  started: { label: 'Running', badge: 'status-running', icon: RunningIcon },
  failure: { label: 'Failed', badge: 'status-failed', icon: XCircle },
  queued: { label: 'Queued', badge: 'status-queued', icon: Clock3 },
  retry: { label: 'Retry', badge: 'status-queued', icon: AlertCircle },
}

export function StatusBadge({ state }: { state: TaskState }) {
  const meta = STATE_META[state]
  const Icon = meta.icon
  return (
    <span className={`status-badge ${meta.badge}`}>
      <Icon size={13} />
      {meta.label}
    </span>
  )
}
