'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Send, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { SEVERITY_LABEL } from './constants'
import {
  createChannel,
  deleteChannel,
  fetchChannels,
  testChannel,
  updateChannel,
} from './fetch-alerts'
import type { ChannelTestResult, Severity } from './types'

export function ChannelsSection() {
  const qc = useQueryClient()
  const { data: channels = [] } = useQuery({
    queryKey: ['alerts', 'channels'],
    queryFn: fetchChannels,
  })
  const invalidate = () => qc.invalidateQueries({ queryKey: ['alerts', 'channels'] })

  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [minSeverity, setMinSeverity] = useState<Severity>('warning')
  const [testResults, setTestResults] = useState<Record<string, ChannelTestResult>>({})

  const addMut = useMutation({
    mutationFn: () =>
      createChannel({
        name: name.trim(),
        type: 'webhook',
        config: { url: url.trim() },
        min_severity: minSeverity,
      }),
    onSuccess: () => {
      setAdding(false)
      setName('')
      setUrl('')
      invalidate()
    },
  })

  const delMut = useMutation({ mutationFn: deleteChannel, onSuccess: invalidate })
  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      updateChannel(id, { enabled }),
    onSuccess: invalidate,
  })
  const testMut = useMutation({
    mutationFn: testChannel,
    onSuccess: (res, id) => setTestResults((prev) => ({ ...prev, [id]: res })),
  })

  return (
    <section className="panel tasks-panel">
      <div className="panel-heading tasks-heading">
        <div>
          <h2>Notification channels</h2>
          <p>Where firing and resolved alerts are sent (webhooks for now)</p>
        </div>
        {!adding && (
          <button className="outline-button small" onClick={() => setAdding(true)}>
            <Plus size={14} /> Add webhook
          </button>
        )}
      </div>

      {adding && (
        <div className="grid gap-3 px-5 pb-4 md:grid-cols-[1fr_2fr_auto_auto]">
          <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <Input
            placeholder="https://hooks.example.com/…"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <Select value={minSeverity} onValueChange={(v) => v && setMinSeverity(v as Severity)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="warning">≥ {SEVERITY_LABEL.warning}</SelectItem>
              <SelectItem value="critical">≥ {SEVERITY_LABEL.critical}</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex gap-2">
            <Button onClick={() => addMut.mutate()} disabled={!name.trim() || !url.trim()}>
              Add
            </Button>
            <Button variant="ghost" onClick={() => setAdding(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Channel</th>
              <th>Destination</th>
              <th>Min severity</th>
              <th>Enabled</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {channels.length === 0 ? (
              <tr>
                <td colSpan={5} className="muted-cell" style={{ textAlign: 'center' }}>
                  No channels — alerts fire but nothing is notified.
                </td>
              </tr>
            ) : (
              channels.map((c) => (
                <tr key={c.id}>
                  <td className="font-medium">{c.name}</td>
                  <td className="mono muted-cell max-w-[280px] truncate">
                    {String(c.config.url ?? '')}
                    {testResults[c.id] && (
                      <span
                        className="ml-2"
                        style={{ color: testResults[c.id].ok ? '#58cdbb' : '#e4877f' }}
                      >
                        {testResults[c.id].ok ? '✓' : '✗'} {testResults[c.id].detail}
                      </span>
                    )}
                  </td>
                  <td className="muted-cell">≥ {c.min_severity}</td>
                  <td>
                    <button
                      className="text-[10px] font-semibold"
                      style={{ color: c.enabled ? '#58cdbb' : '#6d7e86' }}
                      onClick={() => toggleMut.mutate({ id: c.id, enabled: !c.enabled })}
                    >
                      {c.enabled ? 'ON' : 'OFF'}
                    </button>
                  </td>
                  <td>
                    <div className="flex items-center justify-end gap-2">
                      <button
                        title="Send test"
                        className="text-muted-foreground hover:text-foreground"
                        onClick={() => testMut.mutate(c.id)}
                        disabled={testMut.isPending}
                      >
                        <Send size={13} />
                      </button>
                      <button
                        title="Delete"
                        className="text-muted-foreground hover:text-foreground"
                        onClick={() => {
                          if (confirm(`Delete channel "${c.name}"?`)) delMut.mutate(c.id)
                        }}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
