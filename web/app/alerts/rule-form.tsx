'use client'

import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  ALLOWED_SCOPES,
  RULE_TYPE_HELP,
  RULE_TYPE_LABEL,
  SCOPE_LABEL,
  SEVERITY_LABEL,
  THRESHOLD_UNIT,
  WINDOWED_TYPES,
} from './constants'
import type {
  AlertRuleInput,
  AlertRuleOut,
  ComparisonOperator,
  RuleType,
  ScopeType,
  Severity,
} from './types'

const RULE_TYPES: RuleType[] = ['queue_backlog', 'failure_rate', 'worker_down', 'stuck_task']
const OPERATORS: { value: ComparisonOperator; label: string }[] = [
  { value: 'gt', label: 'is above (>)' },
  { value: 'gte', label: 'is at least (≥)' },
  { value: 'lt', label: 'is below (<)' },
  { value: 'lte', label: 'is at most (≤)' },
]
const DEFAULT_THRESHOLD: Record<RuleType, number> = {
  queue_backlog: 100,
  failure_rate: 0.1,
  worker_down: 120,
  stuck_task: 900,
}

interface Draft {
  name: string
  type: RuleType
  scope: ScopeType
  scope_value: string
  operator: ComparisonOperator
  threshold: string // raw input; ratio shown as percent
  window_seconds: string
  for_seconds: string
  severity: Severity
}

function toDraft(rule?: AlertRuleOut): Draft {
  if (!rule) {
    return {
      name: '',
      type: 'queue_backlog',
      scope: 'global',
      scope_value: '',
      operator: 'gt',
      threshold: String(DEFAULT_THRESHOLD.queue_backlog),
      window_seconds: '3600',
      for_seconds: '60',
      severity: 'warning',
    }
  }
  const unit = THRESHOLD_UNIT[rule.type]
  return {
    name: rule.name,
    type: rule.type,
    scope: rule.scope,
    scope_value: rule.scope_value ?? '',
    operator: rule.operator,
    threshold: unit === 'ratio' ? String(rule.threshold * 100) : String(rule.threshold),
    window_seconds: String(rule.window_seconds ?? 3600),
    for_seconds: String(rule.for_seconds),
    severity: rule.severity,
  }
}

export function RuleForm({
  rule,
  onSubmit,
  onCancel,
  busy,
  error,
}: {
  rule?: AlertRuleOut
  onSubmit: (body: AlertRuleInput) => void
  onCancel: () => void
  busy?: boolean
  error?: string | null
}) {
  const editing = Boolean(rule)
  const [d, setD] = useState<Draft>(() => toDraft(rule))
  const unit = THRESHOLD_UNIT[d.type]
  const windowed = WINDOWED_TYPES.includes(d.type)
  const scopes = ALLOWED_SCOPES[d.type]

  const set = (patch: Partial<Draft>) => setD((prev) => ({ ...prev, ...patch }))

  const onTypeChange = (type: RuleType) => {
    const nextScopes = ALLOWED_SCOPES[type]
    setD((prev) => ({
      ...prev,
      type,
      scope: nextScopes.includes(prev.scope) ? prev.scope : nextScopes[0],
      threshold:
        THRESHOLD_UNIT[type] === 'ratio'
          ? String(DEFAULT_THRESHOLD[type] * 100)
          : String(DEFAULT_THRESHOLD[type]),
    }))
  }

  const thresholdHint = useMemo(() => {
    if (unit === 'ratio') return 'percent — e.g. 15 means 15% of tasks failed'
    if (unit === 'seconds') return 'seconds — e.g. 900 = 15 minutes'
    return 'number of pending tasks'
  }, [unit])

  const submit = () => {
    const rawThreshold = Number(d.threshold)
    onSubmit({
      name: d.name.trim(),
      type: d.type,
      scope: d.scope,
      scope_value: d.scope === 'global' ? null : d.scope_value.trim(),
      operator: d.operator,
      threshold: unit === 'ratio' ? rawThreshold / 100 : rawThreshold,
      window_seconds: windowed ? Number(d.window_seconds) : null,
      for_seconds: Number(d.for_seconds),
      severity: d.severity,
    })
  }

  return (
    <div className="panel" style={{ padding: 20 }}>
      <h3 className="mb-4 text-sm font-semibold">{editing ? 'Edit rule' : 'New rule'}</h3>
      <div className="grid gap-4 md:grid-cols-2">
        <Labeled label="Name" className="md:col-span-2">
          <Input
            value={d.name}
            onChange={(e) => set({ name: e.target.value })}
            placeholder="e.g. Emails queue backing up"
          />
        </Labeled>

        <Labeled label="Condition" hint={RULE_TYPE_HELP[d.type]}>
          <Pick value={d.type} onChange={(v) => onTypeChange(v as RuleType)}>
            {RULE_TYPES.map((t) => (
              <SelectItem key={t} value={t}>
                {RULE_TYPE_LABEL[t]}
              </SelectItem>
            ))}
          </Pick>
        </Labeled>

        <Labeled label="Scope">
          <Pick
            value={d.scope}
            onChange={(v) => set({ scope: v as ScopeType })}
            disabled={editing}
          >
            {scopes.map((s) => (
              <SelectItem key={s} value={s}>
                {SCOPE_LABEL[s]}
              </SelectItem>
            ))}
          </Pick>
        </Labeled>

        {d.scope !== 'global' && (
          <Labeled label={SCOPE_LABEL[d.scope]} className="md:col-span-2">
            <Input
              value={d.scope_value}
              onChange={(e) => set({ scope_value: e.target.value })}
              placeholder={
                d.scope === 'queue' ? 'queue name' : d.scope === 'worker' ? 'worker id' : 'task name'
              }
              disabled={editing}
            />
          </Labeled>
        )}

        <Labeled label="When value…">
          <Pick value={d.operator} onChange={(v) => set({ operator: v as ComparisonOperator })}>
            {OPERATORS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </Pick>
        </Labeled>

        <Labeled label="Threshold" hint={thresholdHint}>
          <Input
            type="number"
            value={d.threshold}
            onChange={(e) => set({ threshold: e.target.value })}
          />
        </Labeled>

        {windowed && (
          <Labeled label="Measured over (seconds)" hint="trailing window, e.g. 3600 = 1h">
            <Input
              type="number"
              value={d.window_seconds}
              onChange={(e) => set({ window_seconds: e.target.value })}
            />
          </Labeled>
        )}

        <Labeled label="Hold for (seconds)" hint="condition must stay true this long before firing">
          <Input
            type="number"
            value={d.for_seconds}
            onChange={(e) => set({ for_seconds: e.target.value })}
          />
        </Labeled>

        <Labeled label="Severity">
          <Pick value={d.severity} onChange={(v) => set({ severity: v as Severity })}>
            <SelectItem value="warning">{SEVERITY_LABEL.warning}</SelectItem>
            <SelectItem value="critical">{SEVERITY_LABEL.critical}</SelectItem>
          </Pick>
        </Labeled>
      </div>

      {error && <p className="text-destructive mt-3 text-xs">{error}</p>}

      <div className="mt-5 flex gap-2">
        <Button onClick={submit} disabled={busy || !d.name.trim()}>
          {editing ? 'Save changes' : 'Create rule'}
        </Button>
        <Button variant="ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
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

function Pick({
  value,
  onChange,
  disabled,
  children,
}: {
  value: string
  onChange: (v: string) => void
  disabled?: boolean
  children: React.ReactNode
}) {
  return (
    <Select value={value} onValueChange={(v) => v && onChange(v)} disabled={disabled}>
      <SelectTrigger className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>{children}</SelectContent>
    </Select>
  )
}
