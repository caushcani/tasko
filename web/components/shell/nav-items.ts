import type { LetterKey } from '@tanstack/hotkeys'
import { Bell, Boxes, Layers3, LayoutDashboard, Server, TimerReset } from 'lucide-react'
import type { ComponentType } from 'react'

export interface NavItem {
  label: string
  icon: ComponentType<{ size?: number }>
  /** Not-yet-built pages stay null — rendered as an inert, dimmed button. */
  href: string | null
  group: 'monitor' | 'manage'
  /** Letter for the "G <letter>" jump sequence (see lib/hotkeys/registry.ts) —
   * uppercase, matching @tanstack/hotkeys' `LetterKey` (matching is
   * case-insensitive, the type just standardizes on uppercase). Omitted for
   * not-yet-built items — nothing to jump to. */
  hotkey?: LetterKey
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Overview', icon: LayoutDashboard, href: '/', group: 'monitor', hotkey: 'O' },
  { label: 'Tasks', icon: Boxes, href: '/tasks', group: 'monitor', hotkey: 'T' },
  { label: 'Workers', icon: Server, href: '/workers', group: 'monitor', hotkey: 'W' },
  { label: 'Queues', icon: Layers3, href: '/queues', group: 'monitor', hotkey: 'Q' },
  { label: 'Schedules', icon: TimerReset, href: '/schedules', group: 'monitor', hotkey: 'S' },
  { label: 'Alerts', icon: Bell, href: '/alerts', group: 'manage', hotkey: 'A' },
]

export function titleFor(pathname: string): string {
  if (pathname === '/') return 'Overview'
  if (pathname === '/tasks') return 'Tasks'
  if (pathname.startsWith('/tasks/')) return 'Task detail'
  if (pathname === '/workers') return 'Workers'
  if (pathname.startsWith('/workers/')) return 'Worker detail'
  if (pathname === '/queues') return 'Queues'
  if (pathname.startsWith('/queues/')) return 'Queue detail'
  if (pathname === '/schedules') return 'Schedules'
  if (pathname.startsWith('/schedules/')) return 'Schedule detail'
  if (pathname.startsWith('/alerts')) return 'Alerts'
  return 'Tasko'
}

export function isNavItemActive(item: NavItem, pathname: string): boolean {
  if (!item.href) return false
  return item.href === '/' ? pathname === '/' : pathname.startsWith(item.href)
}
