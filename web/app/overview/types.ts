// Mirrors tasko_core.modules.stats.schemas.

export interface Metric {
  value: number
  previous: number
}

export interface OverviewOut {
  tasks_processed: Metric
  success_rate: Metric
  avg_duration_ms: Metric
  workers_online: number
  workers_known: number
}

export interface ThroughputBucket {
  start: string
  completed: number
  failed: number
}

export interface ThroughputOut {
  window: string
  bucket_seconds: number
  buckets: ThroughputBucket[]
  total_completed: number
  total_failed: number
}

export type ThroughputWindow = '1h' | '24h' | '7d'
