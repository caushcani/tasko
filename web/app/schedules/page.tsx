import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query'
import { parseSort, type ServerQueryState } from '@/lib/table/url-state'
import { fetchSchedules } from './fetch-schedules'
import { loadSchedulesSearchParams } from './search-params'
import { SchedulesTable } from './schedules-table'

interface SchedulesPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}

export default async function SchedulesPage({ searchParams }: SchedulesPageProps) {
  const { offset, limit, sort, q } = await loadSchedulesSearchParams(searchParams)
  const params: ServerQueryState = { offset, limit, sort: parseSort(sort), search: q }

  const queryClient = new QueryClient()
  await queryClient.prefetchQuery({
    queryKey: ['schedules', params],
    queryFn: () => fetchSchedules(params),
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
            Schedules<span className="heading-period">.</span>
          </h1>
          <p>Every recurring task the scheduler is registered to kick — with its next and last run.</p>
        </div>
      </div>

      <section className="panel tasks-panel" style={{ padding: '20px' }}>
        <SchedulesTable />
      </section>
    </HydrationBoundary>
  )
}
