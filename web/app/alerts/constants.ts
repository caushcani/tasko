import type {
  ComparisonOperator,
  RuleState,
  RuleType,
  ScopeType,
  Severity,
} from './types'

export const RULE_TYPE_LABEL: Record<RuleType, string> = {
  queue_backlog: 'Queue backlog',
  failure_rate: 'Failure rate',
  worker_down: 'Worker offline',
  stuck_task: 'Stuck task',
}

export const RULE_TYPE_HELP: Record<RuleType, string> = {
  queue_backlog: 'Pending tasks sitting on a queue (or the whole fleet).',
  failure_rate: 'Share of tasks that failed over a trailing window.',
  worker_down: 'Seconds since a worker last sent a heartbeat.',
  stuck_task: 'Age of the longest-running task that never finished.',
}

export const SCOPE_LABEL: Record<ScopeType, string> = {
  global: 'Fleet-wide',
  queue: 'Queue',
  task_name: 'Task name',
  worker: 'Worker',
}

// Mirrors tasko_core.modules.alerts.enums.ALLOWED_SCOPES
export const ALLOWED_SCOPES: Record<RuleType, ScopeType[]> = {
  queue_backlog: ['global', 'queue'],
  failure_rate: ['global', 'queue', 'task_name'],
  worker_down: ['global', 'worker'],
  stuck_task: ['global', 'queue', 'task_name', 'worker'],
}

export const WINDOWED_TYPES: RuleType[] = ['failure_rate']

/** unit → how the threshold field behaves in the form */
export const THRESHOLD_UNIT: Record<RuleType, 'tasks' | 'ratio' | 'seconds'> = {
  queue_backlog: 'tasks',
  failure_rate: 'ratio',
  worker_down: 'seconds',
  stuck_task: 'seconds',
}

export const OPERATOR_SYMBOL: Record<ComparisonOperator, string> = {
  gt: '>',
  gte: '≥',
  lt: '<',
  lte: '≤',
}

export const SEVERITY_LABEL: Record<Severity, string> = {
  warning: 'Warning',
  critical: 'Critical',
}

export const STATE_LABEL: Record<RuleState, string> = {
  ok: 'OK',
  pending: 'Pending',
  firing: 'Firing',
}

/** Render a threshold or measured value for its unit (0.15 → "15%", 900 → "15m"). */
export function formatThreshold(value: number, unit: 'tasks' | 'ratio' | 'seconds'): string {
  if (unit === 'ratio') {
    const pct = value * 100
    return `${pct % 1 === 0 ? pct : pct.toFixed(1)}%`
  }
  if (unit === 'seconds') {
    if (value >= 3600) return `${(value / 3600).toFixed(value % 3600 === 0 ? 0 : 1)}h`
    if (value >= 60) return `${(value / 60).toFixed(value % 60 === 0 ? 0 : 1)}m`
    return `${Math.round(value)}s`
  }
  return String(Math.round(value))
}

export function formatDurationShort(seconds: number): string {
  if (seconds <= 0) return 'immediately'
  if (seconds >= 3600) return `${Math.round(seconds / 3600)}h`
  if (seconds >= 60) return `${Math.round(seconds / 60)}m`
  return `${seconds}s`
}
