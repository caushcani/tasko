import { apiFetch, ApiError } from '@/lib/api/client'
import type { QueueOut } from './types'

// GET /api/queues is a live read off the broker (Redis SCAN), not a SQL
// query — bare unpaginated list, sort/search happen client-side.
export async function fetchQueues(): Promise<QueueOut[]> {
  return apiFetch<QueueOut[]>('/api/queues')
}

export async function fetchQueueOrNull(name: string): Promise<QueueOut | null> {
  try {
    return await apiFetch<QueueOut>(`/api/queues/${encodeURIComponent(name)}`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}
