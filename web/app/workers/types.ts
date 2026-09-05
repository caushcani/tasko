// Mirrors tasko_core.modules.workers.schemas.WorkerOut.

export interface WorkerOut {
  id: string
  queues: string[]
  active_tasks: number
  first_seen_at: string
  last_heartbeat_at: string
}
