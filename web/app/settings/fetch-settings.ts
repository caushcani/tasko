import { apiFetch } from '@/lib/api/client'
import type { SettingsOut, SettingsUpdate, SmtpTestResult } from './types'

export function fetchSettings(): Promise<SettingsOut> {
  return apiFetch<SettingsOut>('/api/settings')
}

export function updateSettings(body: SettingsUpdate): Promise<SettingsOut> {
  return apiFetch<SettingsOut>('/api/settings', undefined, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function testSmtp(to: string): Promise<SmtpTestResult> {
  return apiFetch<SmtpTestResult>('/api/settings/smtp/test', undefined, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ to }),
  })
}
