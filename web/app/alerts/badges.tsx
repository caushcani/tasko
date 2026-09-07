import { AlertTriangle, CircleCheck, CircleDot, Loader } from 'lucide-react'
import type { RuleState, Severity } from './types'

export function SeverityBadge({ severity }: { severity: Severity }) {
  const critical = severity === 'critical'
  return (
    <span
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide"
      style={
        critical
          ? { background: '#3a1d1d', color: '#e4877f' }
          : { background: '#3a331d', color: '#e1a456' }
      }
    >
      <AlertTriangle size={11} />
      {severity}
    </span>
  )
}

const STATE_STYLE: Record<RuleState, { bg: string; fg: string; icon: typeof CircleDot }> = {
  ok: { bg: '#17332e', fg: '#58cdbb', icon: CircleCheck },
  pending: { bg: '#33311d', fg: '#e1a456', icon: Loader },
  firing: { bg: '#3a1d1d', fg: '#e4877f', icon: CircleDot },
}

export function StateBadge({ state }: { state: RuleState }) {
  const s = STATE_STYLE[state]
  const Icon = s.icon
  return (
    <span
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
      style={{ background: s.bg, color: s.fg }}
    >
      <Icon size={11} />
      {state}
    </span>
  )
}
