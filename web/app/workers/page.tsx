import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query'
import { parseSort, type ServerQueryState } from '@/lib/table/url-state'
import { fetchWorkers } from './fetch-workers'
import { loadWorkersSearchParams } from './search-params'
import { WorkersTable } from './workers-table'

interface WorkersPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}

export default async function WorkersPage({ searchParams }: WorkersPageProps) {
  const { offset, limit, sort, q } = await loadWorkersSearchParams(searchParams)
  const params: ServerQueryState = { offset, limit, sort: parseSort(sort), search: q }

  const queryClient = new QueryClient()
  await queryClient.prefetchQuery({
    queryKey: ['workers', params],
    queryFn: () => fetchWorkers(params),
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
            Workers<span className="heading-period">.</span>
          </h1>
          <p>Every worker that has sent a heartbeat within the liveness window.</p>
        </div>
      </div>

      <section className="panel tasks-panel" style={{ padding: '20px' }}>
        <WorkersTable />
      </section>
    </HydrationBoundary>
  )
}
