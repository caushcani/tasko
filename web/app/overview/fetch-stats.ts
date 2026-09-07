import { apiFetch } from '@/lib/api/client'
import type { OverviewOut, ThroughputOut, ThroughputWindow } from './types'

// GET /api/stats/* — read-only aggregates for the Overview page.
export async function fetchOverview(): Promise<OverviewOut> {
  return apiFetch<OverviewOut>('/api/stats/overview')
}

export async function fetchThroughput(window: ThroughputWindow): Promise<ThroughputOut> {
  return apiFetch<ThroughputOut>('/api/stats/throughput', { window })
}

export interface HealthOut {
  status: string
  version: string
  adapters: string[]
}

export async function fetchHealth(): Promise<HealthOut> {
  return apiFetch<HealthOut>('/healthz')
}
