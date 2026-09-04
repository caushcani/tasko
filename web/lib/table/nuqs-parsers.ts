// Maps a FilterField's `type` to the nuqs parser its URL param uses. One
// lookup, same pattern as sort's serialize/parse pair — a module wires its
// FilterBar to the URL with `useQueryStates(Object.fromEntries(fields.map((f)
// => [f.field, parserFor(f)])))` and gets shareable/back-button-safe filter
// state for free.

import { parseAsArrayOf, parseAsJson, parseAsString, type SingleParserBuilder } from "nuqs"
import type { DateRangeValue, FilterField, NumberRangeValue } from "./filter-types"

// Each branch's concrete type differs (string vs string[] vs an object) — the
// heterogeneous map this feeds (one parser per filter field, built from a
// runtime FilterField[]) can't be typed more precisely than `any` without
// generics fighting the dynamic construction. Callers get real types back
// from `useQueryStates` for the fields they declare statically.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function parserFor(field: FilterField): SingleParserBuilder<any> {
  switch (field.type) {
    case "text":
      return parseAsString
    case "select":
      return field.multiple ? parseAsArrayOf(parseAsString) : parseAsString
    case "daterange":
      return parseAsJson<DateRangeValue>((v) => v as DateRangeValue)
    case "numberrange":
      return parseAsJson<NumberRangeValue>((v) => v as NumberRangeValue)
  }
}
