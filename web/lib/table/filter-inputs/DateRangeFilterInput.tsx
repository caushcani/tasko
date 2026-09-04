"use client"

import { Input } from "@/components/ui/input"
import type { DateRangeFilterField, DateRangeValue } from "../filter-types"
import type { FilterInputProps } from "./types"

export function DateRangeFilterInput({
  config,
  value,
  onChange,
}: FilterInputProps<DateRangeFilterField>) {
  const range = (value as DateRangeValue | undefined) ?? {}

  const emit = (next: DateRangeValue) =>
    onChange(next.from || next.to ? next : undefined)

  return (
    <div className="flex items-center gap-1.5" title={config.label}>
      <Input
        type="date"
        value={range.from ?? ""}
        onChange={(e) => emit({ ...range, from: e.target.value || undefined })}
        className="w-36"
      />
      <span className="text-muted-foreground text-xs">–</span>
      <Input
        type="date"
        value={range.to ?? ""}
        onChange={(e) => emit({ ...range, to: e.target.value || undefined })}
        className="w-36"
      />
    </div>
  )
}
