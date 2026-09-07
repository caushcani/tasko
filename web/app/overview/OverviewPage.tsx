'use client'

import { useQuery } from '@tanstack/react-query'
import { Database, Pause, Play } from 'lucide-react'
import { useState } from 'react'
import { fetchHealth } from './fetch-stats'
import { OverviewMetrics } from './OverviewMetrics'
import { QueueHealth } from './QueueHealth'
import { RecentTasks } from './RecentTasks'
import { ThroughputChart } from './ThroughputChart'

export function OverviewPage() {
  // "Pause monitoring" stops the 10s auto-refresh on every panel. There's no
  // websocket wired yet — this is polling — but the control is real.
  const [paused, setPaused] = useState(false)
  const live = !paused

  const { data: health, isError } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: live ? 30_000 : false,
  })

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="live-indicator" />
            {live ? 'Live monitoring' : 'Monitoring paused'}
          </div>
          <h1>
            Overview<span className="heading-period">.</span>
          </h1>
          <p>Fleet health across your Taskiq workers and queues.</p>
        </div>
        <div className="heading-actions">
          <button className="outline-button" onClick={() => setPaused((p) => !p)}>
            {paused ? <Play size={15} /> : <Pause size={15} />}
            {paused ? 'Resume' : 'Pause'} monitoring
          </button>
        </div>
      </div>

      <OverviewMetrics live={live} />

      <div className="section-grid">
        <ThroughputChart live={live} />
        <QueueHealth live={live} />
      </div>

      <RecentTasks live={live} />

      <footer className="dashboard-footer">
        <span>
          <span className="footer-dot" />
          {isError ? 'tasko-core unreachable' : 'All systems operational'}
        </span>
        <span>{live ? 'Auto-refreshing every 10s' : 'Paused'}</span>
        <span className="footer-spacer" />
        <span>
          <Database size={14} /> tasko-core {health ? `v${health.version}` : ''}
        </span>
      </footer>
    </>
  )
}
