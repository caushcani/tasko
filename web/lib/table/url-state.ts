// The URL <-> ServerQueryState bridge. `sort` serializes to the exact
// "-updated_at,name" format tasko-core's `list_params` already parses —
// one format, both ends, no translation layer.

export interface SortState {
  id: string
  desc: boolean
}

export interface ServerQueryState {
  offset: number
  limit: number
  sort: SortState[]
  search: string
}

export function serializeSort(sort: SortState[]): string | undefined {
  if (!sort.length) return undefined
  return sort.map((s) => (s.desc ? `-${s.id}` : s.id)).join(",")
}

export function parseSort(param: string | null | undefined): SortState[] {
  if (!param) return []
  return param
    .split(",")
    .map((token) => token.trim())
    .filter(Boolean)
    .map((token) => ({
      id: token.startsWith("-") ? token.slice(1) : token,
      desc: token.startsWith("-"),
    }))
}
