"use client"

import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api/client"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { SelectFilterField, SelectOption } from "../filter-types"
import type { FilterInputProps } from "./types"

export function SelectFilterInput({
  config,
  value,
  onChange,
}: FilterInputProps<SelectFilterField>) {
  // Static `options` render immediately; `optionsUrl` (fetched, cached 5min)
  // takes over once it resolves — lets a field ship a fallback while the
  // real list (queues, workers, ...) loads.
  const { data: options } = useQuery({
    queryKey: ["filter-options", config.optionsUrl],
    queryFn: () => apiFetch<SelectOption[]>(config.optionsUrl as string),
    enabled: Boolean(config.optionsUrl),
    staleTime: 5 * 60 * 1000,
    initialData: config.options,
  })

  if (config.multiple) {
    const selected = Array.isArray(value) ? (value as string[]) : []
    return (
      <Select
        multiple
        value={selected}
        onValueChange={(next) => onChange(next.length ? next : undefined)}
      >
        <SelectTrigger className="w-40">
          <SelectValue placeholder={config.label} />
        </SelectTrigger>
        <SelectContent>
          {(options ?? []).map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    )
  }

  const current = typeof value === "string" ? value : null
  return (
    <Select value={current} onValueChange={(next) => onChange(next ?? undefined)}>
      <SelectTrigger className="w-40">
        <SelectValue placeholder={config.label} />
      </SelectTrigger>
      <SelectContent>
        {(options ?? []).map((opt) => (
          <SelectItem key={opt.value} value={opt.value}>
            {opt.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
