"use client"

import { Input } from "@/components/ui/input"
import type { NumberRangeFilterField, NumberRangeValue } from "../filter-types"
import type { FilterInputProps } from "./types"

export function NumberRangeFilterInput({
  config,
  value,
  onChange,
}: FilterInputProps<NumberRangeFilterField>) {
  const range = (value as NumberRangeValue | undefined) ?? {}

  const emit = (next: NumberRangeValue) =>
    onChange(next.min !== undefined || next.max !== undefined ? next : undefined)

  const toNumber = (raw: string) => (raw === "" ? undefined : Number(raw))

  return (
    <div className="flex items-center gap-1.5" title={config.label}>
      <Input
        type="number"
        min={config.min}
        max={config.max}
        placeholder="min"
        value={range.min ?? ""}
        onChange={(e) => emit({ ...range, min: toNumber(e.target.value) })}
        className="w-20"
      />
      <span className="text-muted-foreground text-xs">–</span>
      <Input
        type="number"
        min={config.min}
        max={config.max}
        placeholder="max"
        value={range.max ?? ""}
        onChange={(e) => emit({ ...range, max: toNumber(e.target.value) })}
        className="w-20"
      />
    </div>
  )
}
