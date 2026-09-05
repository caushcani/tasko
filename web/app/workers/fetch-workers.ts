import { apiFetch, ApiError } from '@/lib/api/client'
import type { PaginatedResponse } from '@/lib/api/types'
import { serializeSort, type ServerQueryState } from '@/lib/table/url-state'
import type { WorkerOut } from './types'

// Same shape as tasks: PaginatedResponse, offset/limit/sort/q. GET
// /api/workers now runs through the same list-query engine as tasks
// (DB-only — see workers/routes.py for why adapter-native workers aren't
// merged in here).
export async function fetchWorkers(
  params: ServerQueryState,
): Promise<PaginatedResponse<WorkerOut>> {
  return apiFetch<PaginatedResponse<WorkerOut>>('/api/workers', {
    offset: params.offset,
    limit: params.limit,
    sort: serializeSort(params.sort),
    q: params.search || undefined,
  })
}

export async function fetchWorkerOrNull(id: string): Promise<WorkerOut | null> {
  try {
    return await apiFetch<WorkerOut>(`/api/workers/${encodeURIComponent(id)}`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}
