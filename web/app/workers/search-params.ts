// Same idea as app/tasks/search-params.ts: one set of nuqs parsers so the
// server prefetch (page.tsx) and the client hook (useServerTable, inside
// workers-table.tsx) build identical query keys — no hydration mismatch.
// No extra filter fields here (unlike tasks), so no per-field parser map
// needed — just offset/limit/sort/q, imported from "nuqs/server" since this
// runs in a server loader (see lib/table/nuqs-parsers.ts for why not "nuqs").

import { createLoader, parseAsInteger, parseAsString } from 'nuqs/server'

export const workersSearchParams = {
  offset: parseAsInteger.withDefault(0),
  limit: parseAsInteger.withDefault(15),
  sort: parseAsString,
  q: parseAsString.withDefault(''),
}

export const loadWorkersSearchParams = createLoader(workersSearchParams)
