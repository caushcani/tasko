// Mirrors tasko_core.modules.queues.schemas.QueueOut (from the broker
// adapter's QueueStats). `in_flight` / `oldest_message_at` are always
// 0 / null for the Redis adapter — a plain list has no ack queue and the
// message envelope isn't decoded. Shown as "—" in the UI.

export interface QueueOut {
  name: string
  depth: number
  in_flight: number
  oldest_message_at: string | null
  extra: Record<string, unknown>
}
