// Same idea as app/workers/search-params.ts — one set of nuqs parsers shared
// by the server prefetch (page.tsx) and the client hook (useServerTable), so
// the React Query keys match and there's no hydration flash. No extra filter
// fields here, just offset/limit/sort/q. Imported from "nuqs/server" because
// this runs in a server loader.

import { createLoader, parseAsInteger, parseAsString } from 'nuqs/server'

export const schedulesSearchParams = {
  offset: parseAsInteger.withDefault(0),
  limit: parseAsInteger.withDefault(15),
  sort: parseAsString,
  q: parseAsString.withDefault(''),
}

export const loadSchedulesSearchParams = createLoader(schedulesSearchParams)
