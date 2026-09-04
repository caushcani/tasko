import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query'
import { parseSort, type ServerQueryState } from '@/lib/table/url-state'
import { fetchTasks, type TaskFilters } from './fetch-tasks'
import { loadTasksSearchParams } from './search-params'
import { TasksTable } from './tasks-table'

interface TasksPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}

export default async function TasksPage({ searchParams }: TasksPageProps) {
  // TASK_FILTERS is runtime data, so its keys aren't literal types on the
  // loader's inferred return — cast once at this boundary rather than fight
  // nuqs's generic inference for a dynamically-built parser map.
  const { offset, limit, sort, q, name, state, queue, worker_id } =
    (await loadTasksSearchParams(searchParams)) as {
      offset: number
      limit: number
      sort: string | null
      q: string
    } & TaskFilters

  const params: ServerQueryState & TaskFilters = {
    offset,
    limit,
    sort: parseSort(sort),
    search: q,
    name,
    state,
    queue,
    worker_id,
  }

  // Prefetch on the server with the exact query key useServerTable will read
  // client-side, then hand the cache over — first paint shows real data, no
  // loading flash.
  const queryClient = new QueryClient()
  await queryClient.prefetchQuery({
    queryKey: ['tasks', params],
    queryFn: () => fetchTasks(params),
  })

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="live-indicator" />
            Live monitoring
          </div>
          <h1>
            Tasks<span className="heading-period">.</span>
          </h1>
          <p>Every task tasko-core has seen — filter, sort, and search across the fleet.</p>
        </div>
      </div>

      <section className="panel tasks-panel" style={{ padding: '20px' }}>
        <TasksTable />
      </section>
    </HydrationBoundary>
  )
}
