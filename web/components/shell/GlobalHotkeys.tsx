'use client'

import { useRouter } from 'next/navigation'
import { useAppHotkeySequences } from '@/lib/hotkeys/useAppHotkey'
import { NAV_HOTKEYS } from '@/lib/hotkeys/registry'

// Mounted once from DashboardShell. Renders nothing — registers every
// "G <letter>" jump-to-page sequence from NAV_HOTKEYS in a single hook call
// (useHotkeySequences is built for exactly this: a dynamic-length list from
// one call site, rather than one useHotkeySequence per item in a loop).
export function GlobalHotkeys() {
  const router = useRouter()

  useAppHotkeySequences(
    NAV_HOTKEYS.map(({ sequence, href }) => ({
      sequence,
      callback: () => router.push(href),
    })),
  )

  return null
}
