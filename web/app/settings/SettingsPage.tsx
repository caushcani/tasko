'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { fetchSettings, testSmtp, updateSettings } from './fetch-settings'
import type { SettingsOut, SettingsUpdate, SmtpTestResult } from './types'

interface Draft {
  smtp_host: string
  smtp_port: string
  smtp_username: string
  smtp_password: string // empty = leave the stored password unchanged
  smtp_from: string
  smtp_use_tls: boolean
  worker_ttl_seconds: string
  alert_eval_interval_seconds: string
}

function toDraft(s: SettingsOut): Draft {
  return {
    smtp_host: s.smtp_host ?? '',
    smtp_port: s.smtp_port !== null ? String(s.smtp_port) : '',
    smtp_username: s.smtp_username ?? '',
    smtp_password: '',
    smtp_from: s.smtp_from ?? '',
    smtp_use_tls: s.smtp_use_tls,
    worker_ttl_seconds: s.worker_ttl_seconds !== null ? String(s.worker_ttl_seconds) : '',
    alert_eval_interval_seconds:
      s.alert_eval_interval_seconds !== null ? String(s.alert_eval_interval_seconds) : '',
  }
}

export function SettingsPage() {
  const { data } = useQuery({ queryKey: ['settings'], queryFn: fetchSettings })
  if (!data) return null
  return <SettingsForm settings={data} />
}

function SettingsForm({ settings }: { settings: SettingsOut }) {
  const qc = useQueryClient()
  const [d, setD] = useState<Draft>(() => toDraft(settings))
  const set = (patch: Partial<Draft>) => setD((prev) => ({ ...prev, ...patch }))

  const [testTo, setTestTo] = useState('')
  const [testResult, setTestResult] = useState<SmtpTestResult | null>(null)

  const applyFresh = (fresh: SettingsOut) => {
    setD(toDraft(fresh))
    qc.setQueryData(['settings'], fresh)
  }

  const saveSmtpMut = useMutation({
    mutationFn: (body: SettingsUpdate) => updateSettings(body),
    onSuccess: applyFresh,
  })
  const saveTuningMut = useMutation({
    mutationFn: (body: SettingsUpdate) => updateSettings(body),
    onSuccess: applyFresh,
  })
  const testMut = useMutation({
    mutationFn: () => testSmtp(testTo.trim()),
    onSuccess: setTestResult,
  })

  const saveSmtp = () => {
    const body: SettingsUpdate = {
      smtp_host: d.smtp_host.trim() || null,
      smtp_port: d.smtp_port.trim() ? Number(d.smtp_port) : null,
      smtp_username: d.smtp_username.trim() || null,
      smtp_from: d.smtp_from.trim() || null,
      smtp_use_tls: d.smtp_use_tls,
    }
    if (d.smtp_password) body.smtp_password = d.smtp_password
    saveSmtpMut.mutate(body)
  }

  const saveTuning = () => {
    saveTuningMut.mutate({
      worker_ttl_seconds: d.worker_ttl_seconds.trim() ? Number(d.worker_ttl_seconds) : null,
      alert_eval_interval_seconds: d.alert_eval_interval_seconds.trim()
        ? Number(d.alert_eval_interval_seconds)
        : null,
    })
  }

  return (
    <div className="flex flex-col gap-[18px]">
      <div className="page-heading">
        <div>
          <h1>
            Settings<span className="heading-period">.</span>
          </h1>
          <p>Runtime overrides for things you shouldn&apos;t need to redeploy for.</p>
        </div>
      </div>

      <section className="panel" style={{ padding: 20 }}>
        <h3 className="mb-1 text-sm font-semibold">Email notifications</h3>
        <p className="text-muted-foreground mb-4 text-xs">
          SMTP relay used to deliver email alert channels, and the test below.
        </p>

        <div className="grid gap-4 md:grid-cols-2">
          <Labeled label="Host">
            <Input
              value={d.smtp_host}
              onChange={(e) => set({ smtp_host: e.target.value })}
              placeholder="smtp.example.com"
            />
          </Labeled>
          <Labeled label="Port">
            <Input
              type="number"
              value={d.smtp_port}
              onChange={(e) => set({ smtp_port: e.target.value })}
              placeholder="587"
            />
          </Labeled>
          <Labeled label="Username">
            <Input
              value={d.smtp_username}
              onChange={(e) => set({ smtp_username: e.target.value })}
              placeholder="optional"
            />
          </Labeled>
          <Labeled
            label="Password"
            hint={
              settings.smtp_password_set
                ? 'A password is stored — leave blank to keep it'
                : 'No password stored'
            }
          >
            <Input
              type="password"
              value={d.smtp_password}
              onChange={(e) => set({ smtp_password: e.target.value })}
              placeholder={settings.smtp_password_set ? '••••••••' : ''}
            />
          </Labeled>
          <Labeled label="From address" className="md:col-span-2">
            <Input
              value={d.smtp_from}
              onChange={(e) => set({ smtp_from: e.target.value })}
              placeholder="alerts@yourdomain.com"
            />
          </Labeled>
          <Labeled label="Use STARTTLS">
            <button
              type="button"
              className="outline-button small w-fit"
              onClick={() => set({ smtp_use_tls: !d.smtp_use_tls })}
            >
              {d.smtp_use_tls ? 'ON' : 'OFF'}
            </button>
          </Labeled>
        </div>

        {saveSmtpMut.isError && (
          <p className="text-destructive mt-3 text-xs">{(saveSmtpMut.error as Error).message}</p>
        )}

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Button onClick={saveSmtp} disabled={saveSmtpMut.isPending}>
            Save SMTP settings
          </Button>
          <div className="flex items-center gap-2">
            <Input
              value={testTo}
              onChange={(e) => setTestTo(e.target.value)}
              placeholder="you@example.com"
              className="w-[220px]"
            />
            <Button
              variant="ghost"
              onClick={() => testMut.mutate()}
              disabled={testMut.isPending || !testTo.trim()}
            >
              Send test email
            </Button>
          </div>
          {testResult && (
            <span
              className="text-xs"
              style={{ color: testResult.ok ? '#58cdbb' : '#e4877f' }}
            >
              {testResult.ok ? '✓' : '✗'} {testResult.detail}
            </span>
          )}
        </div>
      </section>

      <section className="panel" style={{ padding: 20 }}>
        <h3 className="mb-1 text-sm font-semibold">Fleet tuning</h3>
        <p className="text-muted-foreground mb-4 text-xs">
          Overrides for tasko.yaml — leave a field blank to fall back to the config file default.
        </p>

        <div className="grid gap-4 md:grid-cols-2">
          <Labeled
            label="Worker TTL (seconds)"
            hint="a worker silent longer than this is considered offline"
          >
            <Input
              type="number"
              value={d.worker_ttl_seconds}
              onChange={(e) => set({ worker_ttl_seconds: e.target.value })}
              placeholder="tasko.yaml default"
            />
          </Labeled>
          <Labeled
            label="Alert evaluation interval (seconds)"
            hint="how often the rule engine re-checks every rule"
          >
            <Input
              type="number"
              value={d.alert_eval_interval_seconds}
              onChange={(e) => set({ alert_eval_interval_seconds: e.target.value })}
              placeholder="tasko.yaml default"
            />
          </Labeled>
        </div>

        {saveTuningMut.isError && (
          <p className="text-destructive mt-3 text-xs">
            {(saveTuningMut.error as Error).message}
          </p>
        )}

        <div className="mt-5">
          <Button onClick={saveTuning} disabled={saveTuningMut.isPending}>
            Save fleet tuning
          </Button>
        </div>
      </section>
    </div>
  )
}

function Labeled({
  label,
  hint,
  className,
  children,
}: {
  label: string
  hint?: string
  className?: string
  children: React.ReactNode
}) {
  return (
    <label className={`flex flex-col gap-1.5 ${className ?? ''}`}>
      <span className="text-muted-foreground text-xs tracking-wide uppercase">{label}</span>
      {children}
      {hint && <span className="text-muted-foreground text-[11px]">{hint}</span>}
    </label>
  )
}
