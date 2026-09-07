import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query'
import { fetchQueues } from '@/app/queues/fetch-queues'
import { fetchTasks } from '@/app/tasks/fetch-tasks'
import { OverviewPage } from './overview/OverviewPage'
import { fetchHealth, fetchOverview, fetchThroughput } from './overview/fetch-stats'

// The sidebar/topbar shell lives in components/shell/DashboardShell.tsx
// (mounted from app/layout.tsx) — this page is just the Overview content.
// Server component: prefetch every panel's query with the exact key its client
// component reads, then hand the cache over so first paint shows real data.
export default async function Page() {
  const queryClient = new QueryClient()

  await Promise.all([
    queryClient.prefetchQuery({ queryKey: ['stats', 'overview'], queryFn: fetchOverview }),
    queryClient.prefetchQuery({
      queryKey: ['stats', 'throughput', '24h'],
      queryFn: () => fetchThroughput('24h'),
    }),
    queryClient.prefetchQuery({ queryKey: ['queues'], queryFn: fetchQueues }),
    queryClient.prefetchQuery({
      queryKey: ['tasks', 'recent'],
      queryFn: () =>
        fetchTasks({ offset: 0, limit: 6, sort: [{ id: 'updated_at', desc: true }], search: '' }),
    }),
    queryClient.prefetchQuery({ queryKey: ['health'], queryFn: fetchHealth }),
  ])

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <OverviewPage />
    </HydrationBoundary>
  )
}
