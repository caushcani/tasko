// Mirrors tasko_core.modules.schedules.schemas.ScheduleOut.
// `last_fired_at` / `next_fire_at` are derived server-side — the first from
// task history (runs carrying this schedule_id label), the second computed
// from the cron expression / interval / one-off time.

export interface ScheduleOut {
  id: string
  task_name: string
  source: string
  cron: string | null
  cron_offset: string | null
  scheduled_time: string | null
  interval_seconds: number | null
  args: unknown[]
  kwargs: Record<string, unknown>
  labels: Record<string, unknown>
  first_seen_at: string
  last_seen_at: string
  last_fired_at: string | null
  next_fire_at: string | null
}
