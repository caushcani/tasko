import type { Hotkey } from '@tanstack/hotkeys'
import { NAV_ITEMS } from '@/components/shell/nav-items'

export interface NavHotkey {
  sequence: [Hotkey, Hotkey]
  href: string
  label: string
}

export const NAV_HOTKEYS: NavHotkey[] = NAV_ITEMS.flatMap((item) =>
  item.href && item.hotkey
    ? [{ sequence: ['G', item.hotkey] as [Hotkey, Hotkey], href: item.href, label: item.label }]
    : [],
)
