'use client'

import { useQuery } from '@tanstack/react-query'
import { ArrowUpRight } from 'lucide-react'
import Link from 'next/link'
import { fetchQueues } from '@/app/queues/fetch-queues'

const REFRESH_MS = 10_000
const COLORS = ['cyan', 'blue', 'amber', 'violet']

export function QueueHealth({ live }: { live: boolean }) {
  const { data: queues } = useQuery({
    queryKey: ['queues'],
    queryFn: fetchQueues,
    refetchInterval: live ? REFRESH_MS : false,
  })

  const sorted = [...(queues ?? [])].sort((a, b) => b.depth - a.depth)
  const total = sorted.reduce((sum, q) => sum + q.depth, 0)
  const top = sorted.slice(0, 4)
  const max = Math.max(1, ...top.map((q) => q.depth))

  return (
    <section className="panel queue-panel">
      <div className="panel-heading">
        <div>
          <h2>Queue health</h2>
          <p>Current depth per queue</p>
        </div>
      </div>
      <div className="queue-total">
        <strong>{total.toLocaleString()}</strong>
        <span>pending tasks</span>
      </div>
      <div className="queue-list">
        {top.length === 0 ? (
          <p className="muted-cell" style={{ fontSize: 11 }}>
            No queues holding tasks right now.
          </p>
        ) : (
          top.map((q, i) => (
            <div className="queue-row" key={q.name}>
              <div className="queue-name">
                <i className={`queue-dot ${COLORS[i]}`} />
                {q.name}
                <span>{q.depth.toLocaleString()}</span>
              </div>
              <div className="progress-track">
                <div
                  className={`progress-fill ${COLORS[i]}`}
                  style={{ width: `${Math.round((q.depth / max) * 100)}%` }}
                />
              </div>
            </div>
          ))
        )}
      </div>
      <Link href="/queues" className="text-button">
        View all queues <ArrowUpRight size={14} />
      </Link>
    </section>
  )
}
