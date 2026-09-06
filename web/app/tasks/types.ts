// Mirrors tasko_core.modules.tasks.schemas.{TaskOut,TaskDetailOut}.

export type TaskState = 'queued' | 'started' | 'success' | 'failure' | 'retry'

export interface TaskOut {
  id: string
  name: string
  queue: string
  state: TaskState
  worker_id: string | null
  schedule_id: string | null
  retries: number
  execution_ms: number | null
  queued_at: string | null
  started_at: string | null
  finished_at: string | null
}

export interface TaskDetailOut extends TaskOut {
  args: unknown[]
  kwargs: Record<string, unknown>
  result: Record<string, unknown> | null
  traceback: string | null
}
