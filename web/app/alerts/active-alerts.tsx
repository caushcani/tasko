'use client'

import { useQuery } from '@tanstack/react-query'
import { BellRing } from 'lucide-react'
import { formatRelative } from '@/lib/format'
import { SeverityBadge } from './badges'
import { fetchActiveEvents } from './fetch-alerts'

export function ActiveAlerts() {
  const { data: events = [] } = useQuery({
    queryKey: ['alerts', 'active'],
    queryFn: fetchActiveEvents,
    refetchInterval: 15_000,
  })

  if (events.length === 0) {
    return (
      <section className="panel" style={{ padding: 18 }}>
        <div className="flex items-center gap-2 text-sm">
          <span className="conn-dot" style={{ background: '#58cdbb' }} />
          No alerts firing — the fleet looks healthy.
        </div>
      </section>
    )
  }

  return (
    <section className="panel" style={{ padding: 4 }}>
      <div className="flex items-center gap-2 px-4 pt-3 pb-2 text-sm font-semibold">
        <BellRing size={15} className="text-destructive" />
        {events.length} alert{events.length > 1 ? 's' : ''} firing
      </div>
      <div className="flex flex-col">
        {events.map((e) => (
          <div
            key={e.id}
            className="flex items-center justify-between gap-4 border-t px-4 py-3 text-sm"
            style={{ borderColor: '#223039' }}
          >
            <div className="flex items-center gap-3">
              <SeverityBadge severity={e.severity} />
              <div>
                <div>{e.summary}</div>
                <div className="muted-cell text-[10px]">
                  {e.rule_name} · firing since {formatRelative(e.started_at)}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
