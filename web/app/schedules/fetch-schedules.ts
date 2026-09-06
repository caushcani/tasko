import { apiFetch, ApiError } from '@/lib/api/client'
import type { PaginatedResponse } from '@/lib/api/types'
import { serializeSort, type ServerQueryState } from '@/lib/table/url-state'
import type { ScheduleOut } from './types'

// GET /api/schedules runs through the same list-query engine as tasks/workers
// (DB-backed — rows are synced from a Taskiq ScheduleSource by
// tasko-middleware's TaskoScheduleSource).
export async function fetchSchedules(
  params: ServerQueryState,
): Promise<PaginatedResponse<ScheduleOut>> {
  return apiFetch<PaginatedResponse<ScheduleOut>>('/api/schedules', {
    offset: params.offset,
    limit: params.limit,
    sort: serializeSort(params.sort),
    q: params.search || undefined,
  })
}

export async function fetchScheduleOrNull(id: string): Promise<ScheduleOut | null> {
  try {
    return await apiFetch<ScheduleOut>(`/api/schedules/${encodeURIComponent(id)}`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}
