'use client'

import { useQuery } from '@tanstack/react-query'
import { ArrowDownRight, ArrowUpRight, Gauge, ShieldCheck, Users, Activity } from 'lucide-react'
import { formatDuration } from '@/lib/format'
import { fetchOverview } from './fetch-stats'
import type { OverviewOut } from './types'

const REFRESH_MS = 10_000

export function OverviewMetrics({ live }: { live: boolean }) {
  const { data } = useQuery({
    queryKey: ['stats', 'overview'],
    queryFn: fetchOverview,
    refetchInterval: live ? REFRESH_MS : false,
  })

  return (
    <div className="metric-grid">
      <MetricCard
        label="Tasks processed"
        value={data ? Math.round(data.tasks_processed.value).toLocaleString() : '—'}
        delta={relDelta(data?.tasks_processed)}
        icon={Activity}
      />
      <MetricCard
        label="Success rate"
        value={data ? `${(data.success_rate.value * 100).toFixed(1)}%` : '—'}
        delta={ppDelta(data?.success_rate)}
        icon={ShieldCheck}
      />
      <MetricCard
        label="Avg. duration"
        value={data ? formatDuration(Math.round(data.avg_duration_ms.value)) : '—'}
        delta={relDelta(data?.avg_duration_ms, { upIsGood: false })}
        icon={Gauge}
      />
      <MetricCard
        label="Active workers"
        value={data ? `${data.workers_online} / ${data.workers_known}` : '—'}
        delta={
          data
            ? { text: data.workers_online > 0 ? 'live' : 'none reporting', positive: data.workers_online > 0, arrow: false }
            : null
        }
        sub="heartbeats"
        icon={Users}
      />
    </div>
  )
}

interface Delta {
  text: string
  positive: boolean
  /** show the up/down arrow (false for a plain status line) */
  arrow: boolean
}

/** Relative % change vs the previous window. */
function relDelta(m: OverviewOut['tasks_processed'] | undefined, opts?: { upIsGood?: boolean }): Delta | null {
  if (!m) return null
  const upIsGood = opts?.upIsGood ?? true
  if (m.previous === 0) {
    if (m.value === 0) return { text: 'no change', positive: true, arrow: false }
    return { text: 'new', positive: upIsGood, arrow: false }
  }
  const pct = ((m.value - m.previous) / m.previous) * 100
  const up = pct >= 0
  return {
    text: `${Math.abs(pct).toFixed(1)}%`,
    positive: up === upIsGood,
    arrow: true,
  }
}

/** Percentage-point difference — the right delta for a rate. */
function ppDelta(m: OverviewOut['success_rate'] | undefined): Delta | null {
  if (!m) return null
  const pp = (m.value - m.previous) * 100
  if (m.previous === 0) return { text: 'new', positive: true, arrow: false }
  const up = pp >= 0
  return { text: `${Math.abs(pp).toFixed(1)}pp`, positive: up, arrow: true }
}

function MetricCard({
  label,
  value,
  delta,
  sub = 'vs last 24h',
  icon: Icon,
}: {
  label: string
  value: string
  delta: Delta | null
  sub?: string
  icon: typeof Activity
}) {
  return (
    <div className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <Icon size={16} />
      </div>
      <div className="metric-value">{value}</div>
      <div className={(delta?.positive ?? true) ? 'metric-delta positive' : 'metric-delta negative'}>
        {delta?.arrow && (delta.positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />)}
        {delta?.text ?? '—'}
        <span>{sub}</span>
      </div>
    </div>
  )
}
