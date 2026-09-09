import { apiFetch, ApiError } from '@/lib/api/client'
import type { PaginatedResponse } from '@/lib/api/types'
import { serializeSort, type ServerQueryState } from '@/lib/table/url-state'
import type { TaskDetailOut, TaskGraphOut, TaskOut } from './types'

export interface TaskFilters {
  name?: string | null
  state?: string | null
  queue?: string | null
  worker_id?: string | null
  schedule_id?: string | null
  [key: string]: unknown
}

export async function fetchTasks(
  params: ServerQueryState & TaskFilters,
): Promise<PaginatedResponse<TaskOut>> {
  return apiFetch<PaginatedResponse<TaskOut>>('/api/tasks', {
    offset: params.offset,
    limit: params.limit,
    sort: serializeSort(params.sort),
    q: params.search || undefined,
    name: params.name ?? undefined,
    state: params.state ?? undefined,
    queue: params.queue ?? undefined,
    worker_id: params.worker_id ?? undefined,
    schedule_id: params.schedule_id ?? undefined,
  })
}

/** Resolves to `null` on a 404 (no matching task) — the page calls
 * next/navigation's `notFound()` itself; other errors still throw. */
export async function fetchTaskOrNull(id: string): Promise<TaskDetailOut | null> {
  try {
    return await apiFetch<TaskDetailOut>(`/api/tasks/${encodeURIComponent(id)}`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}

/** The parent/child lineage around a task. `nodes` is just the task itself
 * when it has no recorded lineage. `null` on 404. */
export async function fetchTaskGraph(id: string): Promise<TaskGraphOut | null> {
  try {
    return await apiFetch<TaskGraphOut>(`/api/tasks/${encodeURIComponent(id)}/graph`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}
