// One set of nuqs parsers, used on both sides of the SSR boundary: the
// server loader below (page.tsx's prefetch) and the client's useQueryStates
// (tasks-table.tsx) build their query params identically, so the React Query
// key the server prefetches matches the one the client reads — no hydration
// mismatch, no loading flash on first paint.

import {
  createLoader,
  parseAsInteger,
  parseAsString,
  type ParserMap,
  type SingleParserBuilder,
} from 'nuqs/server'
import { parserFor } from '@/lib/table/nuqs-parsers'
import { TASK_FILTERS } from './filters'

// TASK_FILTERS is runtime data (declarative, per-module), so its field names
// aren't literal types here — the filter parsers come back as a plain index
// signature. `offset`/`limit`/`sort`/`q` stay precisely typed; any filter
// field is still readable, just as `unknown`.
const filterParsers: Record<string, SingleParserBuilder<any>> = Object.fromEntries(
  TASK_FILTERS.map((f) => [f.field, parserFor(f)]),
)

export const tasksSearchParams = {
  offset: parseAsInteger.withDefault(0),
  limit: parseAsInteger.withDefault(50),
  sort: parseAsString,
  q: parseAsString.withDefault(''),
  ...filterParsers,
} satisfies ParserMap

export const loadTasksSearchParams = createLoader(tasksSearchParams)
