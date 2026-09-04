import type { FilterField } from "../filter-types"

export interface FilterInputProps<F extends FilterField = FilterField> {
  config: F
  value: unknown
  onChange: (value: unknown) => void
}
