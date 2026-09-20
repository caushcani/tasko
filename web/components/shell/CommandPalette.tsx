'use client'

import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchTasks } from '@/app/tasks/fetch-tasks'
import { StatusBadge } from '@/app/tasks/status-badge'
import { Dialog, DialogPopup, DialogTitle } from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import { useAppHotkey } from '@/lib/hotkeys/useAppHotkey'
import { NAV_ITEMS } from './nav-items'

const PAGE_ITEMS = NAV_ITEMS.filter((item) => item.href !== null)

interface Entry {
  key: string
  href: string
  render: () => React.ReactNode
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-muted-foreground px-3 pt-2 pb-1 text-[9px] font-semibold tracking-[1.2px] uppercase">
      {children}
    </p>
  )
}

function EntryButton({
  entry,
  active,
  onHover,
  onSelect,
}: {
  entry: Entry
  active: boolean
  onHover: () => void
  onSelect: () => void
}) {
  return (
    <button
      role="option"
      aria-selected={active}
      className={cn(
        'text-foreground flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-left text-sm outline-none',
        active && 'bg-accent text-accent-foreground',
      )}
      onMouseEnter={onHover}
      onClick={onSelect}
    >
      {entry.render()}
    </button>
  )
}

// Cmd+K (Mod+K) from anywhere in the app — this is the "global search" the
// topbar's search box has always hinted at (⌘K badge) but never wired up.
export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [highlight, setHighlight] = useState(0)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useAppHotkey('Mod+K', () => onOpenChange(!open))

  useEffect(() => {
    if (!open) {
      setQuery('')
      setDebouncedQuery('')
      setHighlight(0)
    }
  }, [open])

  useEffect(() => {
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setDebouncedQuery(query), 200)
    return () => clearTimeout(timer.current)
  }, [query])

  const { data: taskResults } = useQuery({
    queryKey: ['command-palette-tasks', debouncedQuery],
    queryFn: () => fetchTasks({ offset: 0, limit: 6, sort: [], search: debouncedQuery }),
    enabled: debouncedQuery.length > 0,
  })

  const pageEntries: Entry[] = useMemo(
    () =>
      PAGE_ITEMS.filter((item) => item.label.toLowerCase().includes(query.toLowerCase())).map(
        (item) => ({
          key: `page:${item.href}`,
          href: item.href as string,
          render: () => (
            <>
              <item.icon size={15} />
              <span>{item.label}</span>
            </>
          ),
        }),
      ),
    [query],
  )

  const taskEntries: Entry[] = useMemo(
    () =>
      (taskResults?.items ?? []).map((task) => ({
        key: `task:${task.id}`,
        href: `/tasks/${task.id}`,
        render: () => (
          <>
            <StatusBadge state={task.state} />
            <span className="flex-1 truncate">{task.name}</span>
            <span className="queue-pill">{task.queue}</span>
          </>
        ),
      })),
    [taskResults],
  )

  const entries = query ? [...pageEntries, ...taskEntries] : pageEntries

  const go = (href: string) => {
    onOpenChange(false)
    router.push(href)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogPopup className="w-[min(560px,92vw)] gap-0 p-0" aria-label="Command palette">
        <DialogTitle>Jump to a page or search tasks</DialogTitle>
        <div className="border-border text-muted-foreground flex items-center gap-2.5 border-b px-4 py-3">
          <Search size={15} />
          <input
            autoFocus
            value={query}
            placeholder="Jump to a page or search tasks…"
            className="text-foreground placeholder:text-muted-foreground flex-1 bg-transparent text-sm outline-none"
            onChange={(e) => {
              setQuery(e.target.value)
              setHighlight(0)
            }}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                e.preventDefault()
                setHighlight((h) => Math.min(h + 1, entries.length - 1))
              } else if (e.key === 'ArrowUp') {
                e.preventDefault()
                setHighlight((h) => Math.max(h - 1, 0))
              } else if (e.key === 'Enter' && entries[highlight]) {
                e.preventDefault()
                go(entries[highlight].href)
              }
            }}
          />
          <kbd className="border-border text-muted-foreground rounded border px-1.5 py-0.5 text-[10px]">
            Esc
          </kbd>
        </div>

        <div className="max-h-80 overflow-y-auto p-1.5" role="listbox">
          {entries.length === 0 ? (
            <p className="text-muted-foreground px-3 py-6 text-center text-sm">
              {query ? `No pages or tasks match "${query}"` : 'No pages to jump to'}
            </p>
          ) : (
            <>
              {pageEntries.length > 0 && <SectionLabel>Pages</SectionLabel>}
              {pageEntries.map((entry) => (
                <EntryButton
                  key={entry.key}
                  entry={entry}
                  active={entries.indexOf(entry) === highlight}
                  onHover={() => setHighlight(entries.indexOf(entry))}
                  onSelect={() => go(entry.href)}
                />
              ))}
              {taskEntries.length > 0 && <SectionLabel>Tasks</SectionLabel>}
              {taskEntries.map((entry) => (
                <EntryButton
                  key={entry.key}
                  entry={entry}
                  active={entries.indexOf(entry) === highlight}
                  onHover={() => setHighlight(entries.indexOf(entry))}
                  onSelect={() => go(entry.href)}
                />
              ))}
            </>
          )}
        </div>
      </DialogPopup>
    </Dialog>
  )
}
