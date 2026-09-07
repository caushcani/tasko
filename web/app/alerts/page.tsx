import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query'
import { AlertsPage } from './AlertsPage'
import { fetchActiveEvents, fetchChannels, fetchEvents, fetchRules } from './fetch-alerts'

export default async function Page() {
  const queryClient = new QueryClient()
  await Promise.all([
    queryClient.prefetchQuery({ queryKey: ['alerts', 'rules'], queryFn: fetchRules }),
    queryClient.prefetchQuery({ queryKey: ['alerts', 'active'], queryFn: fetchActiveEvents }),
    queryClient.prefetchQuery({ queryKey: ['alerts', 'channels'], queryFn: fetchChannels }),
    queryClient.prefetchQuery({
      queryKey: ['alerts', 'events', 0],
      queryFn: () => fetchEvents({ offset: 0, limit: 10, sort: [], search: '' }),
    }),
  ])

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <AlertsPage />
    </HydrationBoundary>
  )
}
