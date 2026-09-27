import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query'
import { fetchSettings } from './fetch-settings'
import { SettingsPage } from './SettingsPage'

export default async function Page() {
  const queryClient = new QueryClient()
  await queryClient.prefetchQuery({ queryKey: ['settings'], queryFn: fetchSettings })

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <SettingsPage />
    </HydrationBoundary>
  )
}
