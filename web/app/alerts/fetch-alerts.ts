import { apiFetch } from '@/lib/api/client'
import type { PaginatedResponse } from '@/lib/api/types'
import { serializeSort, type ServerQueryState } from '@/lib/table/url-state'
import type {
  AlertEventOut,
  AlertRuleInput,
  AlertRuleOut,
  ChannelTestResult,
  NotificationChannelOut,
  Severity,
} from './types'

// --- rules ---

export async function fetchRules(): Promise<AlertRuleOut[]> {
  const res = await apiFetch<PaginatedResponse<AlertRuleOut>>('/api/alerts/rules', { limit: 200 })
  return res.items
}

export function createRule(body: AlertRuleInput): Promise<AlertRuleOut> {
  return apiFetch<AlertRuleOut>('/api/alerts/rules', undefined, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function updateRule(id: string, body: Partial<AlertRuleInput>): Promise<AlertRuleOut> {
  return apiFetch<AlertRuleOut>(`/api/alerts/rules/${id}`, undefined, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function deleteRule(id: string): Promise<unknown> {
  return apiFetch(`/api/alerts/rules/${id}`, undefined, { method: 'DELETE' })
}

export function evaluateRule(id: string): Promise<AlertRuleOut> {
  return apiFetch<AlertRuleOut>(`/api/alerts/rules/${id}/evaluate`, undefined, { method: 'POST' })
}

// --- events ---

export async function fetchEvents(
  params: ServerQueryState & { active?: boolean; severity?: Severity },
): Promise<PaginatedResponse<AlertEventOut>> {
  return apiFetch<PaginatedResponse<AlertEventOut>>('/api/alerts/events', {
    offset: params.offset,
    limit: params.limit,
    sort: serializeSort(params.sort),
    q: params.search || undefined,
    active: params.active,
    severity: params.severity,
  })
}

export async function fetchActiveEvents(): Promise<AlertEventOut[]> {
  const res = await fetchEvents({ offset: 0, limit: 50, sort: [], search: '', active: true })
  return res.items
}

// --- channels ---

export function fetchChannels(): Promise<NotificationChannelOut[]> {
  return apiFetch<NotificationChannelOut[]>('/api/alerts/channels')
}

export function createChannel(body: {
  name: string
  type: 'webhook'
  config: Record<string, unknown>
  min_severity: Severity
  enabled?: boolean
}): Promise<NotificationChannelOut> {
  return apiFetch<NotificationChannelOut>('/api/alerts/channels', undefined, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function updateChannel(
  id: string,
  body: Record<string, unknown>,
): Promise<NotificationChannelOut> {
  return apiFetch<NotificationChannelOut>(`/api/alerts/channels/${id}`, undefined, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function deleteChannel(id: string): Promise<unknown> {
  return apiFetch(`/api/alerts/channels/${id}`, undefined, { method: 'DELETE' })
}

export function testChannel(id: string): Promise<ChannelTestResult> {
  return apiFetch<ChannelTestResult>(`/api/alerts/channels/${id}/test`, undefined, {
    method: 'POST',
  })
}
