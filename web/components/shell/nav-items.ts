import { Boxes, Layers3, LayoutDashboard, Server, TimerReset } from 'lucide-react'
import type { ComponentType } from 'react'

export interface NavItem {
  label: string
  icon: ComponentType<{ size?: number }>
  /** Not-yet-built pages stay null — rendered as an inert, dimmed button. */
  href: string | null
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Overview', icon: LayoutDashboard, href: '/' },
  { label: 'Tasks', icon: Boxes, href: '/tasks' },
  { label: 'Workers', icon: Server, href: '/workers' },
  { label: 'Queues', icon: Layers3, href: null },
  { label: 'Schedules', icon: TimerReset, href: null },
]

export function titleFor(pathname: string): string {
  if (pathname === '/') return 'Overview'
  if (pathname === '/tasks') return 'Tasks'
  if (pathname.startsWith('/tasks/')) return 'Task detail'
  if (pathname === '/workers') return 'Workers'
  if (pathname.startsWith('/workers/')) return 'Worker detail'
  return 'Tasko'
}

export function isNavItemActive(item: NavItem, pathname: string): boolean {
  if (!item.href) return false
  return item.href === '/' ? pathname === '/' : pathname.startsWith(item.href)
}
