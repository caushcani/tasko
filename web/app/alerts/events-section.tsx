'use client'

import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { useState } from 'react'
import { formatRelative } from '@/lib/format'
import { SeverityBadge } from './badges'
import { fetchEvents } from './fetch-alerts'

const PAGE = 10

function duration(startIso: string, endIso: string | null): string {
  const end = endIso ? new Date(endIso).getTime() : Date.now()
  const secs = Math.max(0, Math.round((end - new Date(startIso).getTime()) / 1000))
  if (secs >= 3600) return `${Math.round(secs / 3600)}h`
  if (secs >= 60) return `${Math.round(secs / 60)}m`
  return `${secs}s`
}

export function EventsSection() {
  const [offset, setOffset] = useState(0)
  const { data } = useQuery({
    queryKey: ['alerts', 'events', offset],
    queryFn: () => fetchEvents({ offset, limit: PAGE, sort: [], search: '' }),
    placeholderData: keepPreviousData,
    refetchInterval: 30_000,
  })

  const events = data?.items ?? []
  const total = data?.total_count ?? 0

  return (
    <section className="panel tasks-panel">
      <div className="panel-heading tasks-heading">
        <div>
          <h2>History</h2>
          <p>Every time a rule has fired</p>
        </div>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>Alert</th>
              <th>Rule</th>
              <th>Started</th>
              <th>Duration</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan={6} className="muted-cell" style={{ textAlign: 'center' }}>
                  Nothing has fired yet.
                </td>
              </tr>
            ) : (
              events.map((e) => (
                <tr key={e.id}>
                  <td>
                    <SeverityBadge severity={e.severity} />
                  </td>
                  <td>{e.summary}</td>
                  <td className="muted-cell">{e.rule_name ?? '—'}</td>
                  <td className="muted-cell">{formatRelative(e.started_at)}</td>
                  <td className="mono">{duration(e.started_at, e.resolved_at)}</td>
                  <td
                    className="text-[11px]"
                    style={{ color: e.resolved_at ? '#6d7e86' : '#e4877f' }}
                  >
                    {e.resolved_at ? 'resolved' : 'firing'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {total > PAGE && (
        <div className="flex items-center justify-end gap-3 px-5 py-3 text-xs">
          <button
            className="outline-button small"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE))}
          >
            Prev
          </button>
          <span className="muted-cell">
            {offset + 1}–{Math.min(offset + PAGE, total)} of {total}
          </span>
          <button
            className="outline-button small"
            disabled={offset + PAGE >= total}
            onClick={() => setOffset(offset + PAGE)}
          >
            Next
          </button>
        </div>
      )}
    </section>
  )
}
