'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Play, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { formatRelative } from '@/lib/format'
import { SeverityBadge, StateBadge } from './badges'
import {
  OPERATOR_SYMBOL,
  RULE_TYPE_LABEL,
  SCOPE_LABEL,
  THRESHOLD_UNIT,
  formatDurationShort,
  formatThreshold,
} from './constants'
import {
  createRule,
  deleteRule,
  evaluateRule,
  fetchRules,
  updateRule,
} from './fetch-alerts'
import { RuleForm } from './rule-form'
import type { AlertRuleInput, AlertRuleOut } from './types'

export function RulesSection() {
  const qc = useQueryClient()
  const { data: rules = [] } = useQuery({
    queryKey: ['alerts', 'rules'],
    queryFn: fetchRules,
    refetchInterval: 15_000,
  })

  const [editing, setEditing] = useState<AlertRuleOut | null>(null)
  const [creating, setCreating] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['alerts'] })
  }

  const saveMut = useMutation({
    mutationFn: (body: AlertRuleInput) =>
      editing ? updateRule(editing.id, body) : createRule(body),
    onSuccess: () => {
      setCreating(false)
      setEditing(null)
      setFormError(null)
      invalidate()
    },
    onError: (err: Error) => setFormError(parseError(err.message)),
  })

  const deleteMut = useMutation({
    mutationFn: deleteRule,
    onSuccess: invalidate,
  })

  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => updateRule(id, { enabled }),
    onSuccess: invalidate,
  })

  const evalMut = useMutation({
    mutationFn: evaluateRule,
    onSuccess: invalidate,
  })

  return (
    <section className="panel tasks-panel">
      <div className="panel-heading tasks-heading">
        <div>
          <h2>Rules</h2>
          <p>Conditions the evaluator checks every 30s</p>
        </div>
        {!creating && !editing && (
          <button
            className="outline-button small"
            onClick={() => {
              setCreating(true)
              setFormError(null)
            }}
          >
            <Plus size={14} /> New rule
          </button>
        )}
      </div>

      {(creating || editing) && (
        <div className="px-5 pb-4">
          <RuleForm
            rule={editing ?? undefined}
            busy={saveMut.isPending}
            error={formError}
            onSubmit={(body) => saveMut.mutate(body)}
            onCancel={() => {
              setCreating(false)
              setEditing(null)
              setFormError(null)
            }}
          />
        </div>
      )}

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Rule</th>
              <th>Condition</th>
              <th>Hold</th>
              <th>Severity</th>
              <th>State</th>
              <th>Last check</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rules.length === 0 ? (
              <tr>
                <td colSpan={7} className="muted-cell" style={{ textAlign: 'center' }}>
                  No rules yet — create one to start alerting.
                </td>
              </tr>
            ) : (
              rules.map((rule) => (
                <tr key={rule.id} style={{ opacity: rule.enabled ? 1 : 0.5 }}>
                  <td>
                    <div className="font-medium">{rule.name}</div>
                    <div className="muted-cell text-[10px]">
                      {RULE_TYPE_LABEL[rule.type]} ·{' '}
                      {rule.scope === 'global' ? 'fleet-wide' : `${SCOPE_LABEL[rule.scope]} ${rule.scope_value}`}
                    </div>
                  </td>
                  <td className="mono">
                    {OPERATOR_SYMBOL[rule.operator]}{' '}
                    {formatThreshold(rule.threshold, THRESHOLD_UNIT[rule.type])}
                    {rule.last_value != null && (
                      <span className="muted-cell">
                        {' '}
                        (now {formatThreshold(rule.last_value, THRESHOLD_UNIT[rule.type])})
                      </span>
                    )}
                  </td>
                  <td className="muted-cell">{formatDurationShort(rule.for_seconds)}</td>
                  <td>
                    <SeverityBadge severity={rule.severity} />
                  </td>
                  <td>
                    <StateBadge state={rule.state} />
                  </td>
                  <td className="muted-cell">
                    {rule.last_evaluated_at ? formatRelative(rule.last_evaluated_at) : '—'}
                  </td>
                  <td>
                    <div className="flex items-center justify-end gap-1">
                      <IconBtn
                        title="Evaluate now"
                        onClick={() => evalMut.mutate(rule.id)}
                        disabled={evalMut.isPending}
                      >
                        <Play size={13} />
                      </IconBtn>
                      <IconBtn
                        title={rule.enabled ? 'Disable' : 'Enable'}
                        onClick={() => toggleMut.mutate({ id: rule.id, enabled: !rule.enabled })}
                      >
                        <span className="text-[10px] font-semibold">
                          {rule.enabled ? 'ON' : 'OFF'}
                        </span>
                      </IconBtn>
                      <IconBtn title="Edit" onClick={() => setEditing(rule)}>
                        <Pencil size={13} />
                      </IconBtn>
                      <IconBtn
                        title="Delete"
                        onClick={() => {
                          if (confirm(`Delete rule "${rule.name}"?`)) deleteMut.mutate(rule.id)
                        }}
                      >
                        <Trash2 size={13} />
                      </IconBtn>
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

function IconBtn({
  title,
  onClick,
  disabled,
  children,
}: {
  title: string
  onClick: () => void
  disabled?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      title={title}
      onClick={onClick}
      disabled={disabled}
      className="text-muted-foreground hover:text-foreground flex h-6 min-w-6 items-center justify-center rounded px-1 hover:bg-white/5 disabled:opacity-40"
    >
      {children}
    </button>
  )
}

function parseError(message: string): string {
  try {
    const body = JSON.parse(message)
    if (Array.isArray(body.detail)) return body.detail.map((d: { msg: string }) => d.msg).join('; ')
    if (typeof body.detail === 'string') return body.detail
  } catch {
    /* not json */
  }
  return message
}
