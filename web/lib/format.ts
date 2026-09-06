// Shared display formatters — used by every module's columns/detail views
// (tasks, workers, ...), not just one.

export function formatDuration(ms: number | null): string {
  if (ms == null) return '—'
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`
}

export function formatRelative(iso: string | null): string {
  if (!iso) return '—'
  const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return new Date(iso).toLocaleDateString()
}

export function formatAbsolute(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

// Signed relative time — "in 3h" for the future, "3h ago" for the past.
// Used where a timestamp can be either (a schedule's next run).
export function formatWhen(iso: string | null): string {
  if (!iso) return '—'
  const deltaMs = new Date(iso).getTime() - Date.now()
  const ahead = deltaMs >= 0
  let seconds = Math.round(Math.abs(deltaMs) / 1000)
  const phrase = (value: string) => (ahead ? `in ${value}` : `${value} ago`)
  if (seconds < 60) return phrase(`${seconds}s`)
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return phrase(`${minutes}m`)
  const hours = Math.round(minutes / 60)
  if (hours < 24) return phrase(`${hours}h`)
  const days = Math.round(hours / 24)
  if (days < 7) return phrase(`${days}d`)
  return new Date(iso).toLocaleDateString()
}
