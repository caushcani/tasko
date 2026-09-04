// A module declares its filterable fields as data (mirrors the backend's
// `ListSpec.filterable_fields`), not as one bespoke block of JSX per module.
// The `type` discriminant means every field's props are checked at compile
// time instead of guessed at in a renderer.

export interface BaseFilterField {
  /** Must match the backend ListSpec field name exactly, dotted relation
   * names included (e.g. "worker.last_heartbeat_at"). */
  field: string
  label: string
}

export interface TextFilterField extends BaseFilterField {
  type: "text"
  placeholder?: string
  /** ms to wait after the last keystroke before updating the URL/query. */
  debounceMs?: number
}

export interface SelectOption {
  label: string
  value: string
}

export interface SelectFilterField extends BaseFilterField {
  type: "select"
  options?: SelectOption[]
  /** Fetched via apiFetch; merges with/overrides `options` once loaded. */
  optionsUrl?: string
  multiple?: boolean
}

export interface DateRangeFilterField extends BaseFilterField {
  type: "daterange"
}

export interface NumberRangeFilterField extends BaseFilterField {
  type: "numberrange"
  min?: number
  max?: number
}

export type FilterField =
  | TextFilterField
  | SelectFilterField
  | DateRangeFilterField
  | NumberRangeFilterField

export interface DateRangeValue {
  from?: string
  to?: string
}

export interface NumberRangeValue {
  min?: number
  max?: number
}
