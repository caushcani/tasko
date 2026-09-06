import type { ScheduleOut } from './types'

// A compact, human-ish description of a schedule's cadence. Covers the common
// cron shapes; anything unrecognised falls back to the raw expression. Not a
// full cron parser — a dashboard hint.

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function describeCron(expr: string): string {
  const parts = expr.trim().split(/\s+/)
  if (parts.length !== 5) return expr
  const [min, hour, dom, mon, dow] = parts

  const everyN = (field: string, unit: string) => {
    const m = field.match(/^\*\/(\d+)$/)
    return m ? `every ${m[1]}${unit}` : null
  }

  if (min.startsWith('*/') && hour === '*' && dom === '*' && mon === '*' && dow === '*') {
    return everyN(min, 'm') ?? expr
  }
  if (hour.startsWith('*/') && min === '0' && dom === '*' && mon === '*' && dow === '*') {
    return everyN(hour, 'h') ?? expr
  }
  const isNum = (s: string) => /^\d+$/.test(s)
  if (isNum(min) && isNum(hour) && mon === '*') {
    const at = `${hour.padStart(2, '0')}:${min.padStart(2, '0')}`
    if (dom === '*' && dow === '*') return `daily at ${at}`
    if (dom === '*' && isNum(dow)) return `${DOW[Number(dow) % 7]} at ${at}`
    if (isNum(dom) && dow === '*') return `day ${dom} of the month at ${at}`
  }
  return expr
}

export function formatSchedule(s: ScheduleOut): string {
  if (s.cron) return describeCron(s.cron)
  if (s.interval_seconds != null) {
    const sec = s.interval_seconds
    if (sec % 3600 === 0) return `every ${sec / 3600}h`
    if (sec % 60 === 0) return `every ${sec / 60}m`
    return `every ${sec}s`
  }
  if (s.scheduled_time) return `once at ${new Date(s.scheduled_time).toLocaleString()}`
  return '—'
}

export function scheduleKind(s: ScheduleOut): 'cron' | 'interval' | 'one-off' | 'unknown' {
  if (s.cron) return 'cron'
  if (s.interval_seconds != null) return 'interval'
  if (s.scheduled_time) return 'one-off'
  return 'unknown'
}
