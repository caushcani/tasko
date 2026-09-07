// Mirrors tasko_core.modules.alerts.

export type RuleType = 'queue_backlog' | 'failure_rate' | 'worker_down' | 'stuck_task'
export type ScopeType = 'global' | 'queue' | 'task_name' | 'worker'
export type ComparisonOperator = 'gt' | 'gte' | 'lt' | 'lte'
export type Severity = 'warning' | 'critical'
export type RuleState = 'ok' | 'pending' | 'firing'
export type ChannelType = 'webhook' | 'email'

export interface AlertRuleOut {
  id: string
  name: string
  type: RuleType
  scope: ScopeType
  scope_value: string | null
  operator: ComparisonOperator
  threshold: number
  threshold_unit: 'tasks' | 'ratio' | 'seconds'
  window_seconds: number | null
  for_seconds: number
  severity: Severity
  enabled: boolean
  state: RuleState
  state_since: string
  last_value: number | null
  last_evaluated_at: string | null
  created_at: string
}

export interface AlertRuleInput {
  name: string
  type: RuleType
  scope: ScopeType
  scope_value?: string | null
  operator: ComparisonOperator
  threshold: number
  window_seconds?: number | null
  for_seconds: number
  severity: Severity
  enabled?: boolean
}

export interface AlertEventOut {
  id: string
  rule_id: string
  rule_name: string | null
  severity: Severity
  summary: string
  trigger_value: number
  started_at: string
  resolved_at: string | null
}

export interface NotificationChannelOut {
  id: string
  name: string
  type: ChannelType
  enabled: boolean
  config: Record<string, unknown>
  min_severity: Severity
  created_at: string
}

export interface ChannelTestResult {
  ok: boolean
  detail: string
}
