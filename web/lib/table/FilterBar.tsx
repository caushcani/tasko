"use client"

import type { ComponentType } from "react"
import type { FilterField } from "./filter-types"
import { DateRangeFilterInput } from "./filter-inputs/DateRangeFilterInput"
import { NumberRangeFilterInput } from "./filter-inputs/NumberRangeFilterInput"
import { SelectFilterInput } from "./filter-inputs/SelectFilterInput"
import { TextFilterInput } from "./filter-inputs/TextFilterInput"
import type { FilterInputProps } from "./filter-inputs/types"

// One dispatch component. Adding a filter type later (a boolean toggle, a
// tag picker) means writing one renderer and adding one line here — nothing
// else in the table engine changes.
const RENDERERS: Record<FilterField["type"], ComponentType<FilterInputProps<any>>> = {
  text: TextFilterInput,
  select: SelectFilterInput,
  daterange: DateRangeFilterInput,
  numberrange: NumberRangeFilterInput,
}

export interface FilterBarProps {
  fields: FilterField[]
  value: Record<string, unknown>
  onChange: (field: string, value: unknown) => void
}

export function FilterBar({ fields, value, onChange }: FilterBarProps) {
  if (!fields.length) return null
  return (
    <div className="flex flex-wrap items-center gap-3">
      {fields.map((field) => {
        const Input = RENDERERS[field.type]
        return (
          <Input
            key={field.field}
            config={field}
            value={value[field.field]}
            onChange={(v) => onChange(field.field, v)}
          />
        )
      })}
    </div>
  )
}
