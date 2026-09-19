"use client"

import { useState } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { HotkeysProvider } from "@tanstack/react-hotkeys"
import { NuqsAdapter } from "nuqs/adapters/next/app"

export function Providers({ children }: { children: React.ReactNode }) {
  // One QueryClient per browser tab, created once, not on every render.
  const [queryClient] = useState(() => new QueryClient())

  return (
    <NuqsAdapter>
      <QueryClientProvider client={queryClient}>
        {/* ignoreInputs: without it, typing in a filter box would fire
            single-letter shortcuts like the "g" in a "g t" sequence. */}
        <HotkeysProvider defaultOptions={{ hotkey: { ignoreInputs: true } }}>
          {children}
        </HotkeysProvider>
      </QueryClientProvider>
    </NuqsAdapter>
  )
}
