"use client"

import { useEffect, useRef, useState } from "react"
import { Input } from "@/components/ui/input"
import type { TextFilterField } from "../filter-types"
import type { FilterInputProps } from "./types"

export function TextFilterInput({ config, value, onChange }: FilterInputProps<TextFilterField>) {
  const external = typeof value === "string" ? value : ""
  const [draft, setDraft] = useState(external)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  // Keep in sync with external changes (URL nav, filters reset elsewhere).
  useEffect(() => setDraft(external), [external])

  useEffect(() => () => clearTimeout(timer.current), [])

  return (
    <Input
      value={draft}
      placeholder={config.placeholder ?? config.label}
      onChange={(e) => {
        const next = e.target.value
        setDraft(next)
        clearTimeout(timer.current)
        timer.current = setTimeout(() => onChange(next || undefined), config.debounceMs ?? 300)
      }}
      className="w-40"
    />
  )
}
