// Mirrors tasko_core.modules.settings.

export interface SettingsOut {
  smtp_host: string | null
  smtp_port: number | null
  smtp_username: string | null
  smtp_password_set: boolean
  smtp_from: string | null
  smtp_use_tls: boolean
  worker_ttl_seconds: number | null
  alert_eval_interval_seconds: number | null
  updated_at: string
}

export interface SettingsUpdate {
  smtp_host?: string | null
  smtp_port?: number | null
  smtp_username?: string | null
  smtp_password?: string
  smtp_from?: string | null
  smtp_use_tls?: boolean
  worker_ttl_seconds?: number | null
  alert_eval_interval_seconds?: number | null
}

export interface SmtpTestResult {
  ok: boolean
  detail: string
}
