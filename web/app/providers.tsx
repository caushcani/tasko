"use client"

import { useState } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { NuqsAdapter } from "nuqs/adapters/next/app"

export function Providers({ children }: { children: React.ReactNode }) {
  // One QueryClient per browser tab, created once, not on every render.
  const [queryClient] = useState(() => new QueryClient())

  return (
    <NuqsAdapter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </NuqsAdapter>
  )
}
