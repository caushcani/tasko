// Typed fetch wrapper for tasko-core.
//
// Runs on both sides of the SSR boundary: server components / route
// handlers call it directly against the internal Docker URL, client
// components call it against a publicly reachable one. Point
// TASKO_CORE_URL at the internal address and NEXT_PUBLIC_TASKO_CORE_URL at
// the public one — see docker-compose.yml when a page starts using this
// client-side. NEXT_PUBLIC_* is inlined at build time in a prod build, so a
// container-only env override won't reach an already-built bundle.

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

function baseUrl(): string {
  const url =
    typeof window === "undefined"
      ? process.env.TASKO_CORE_URL
      : process.env.NEXT_PUBLIC_TASKO_CORE_URL
  return url ?? "http://localhost:8000"
}

function buildUrl(path: string, params?: Record<string, unknown>): string {
  const url = new URL(path, baseUrl())
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === "") continue
      if (Array.isArray(value)) {
        for (const item of value) url.searchParams.append(key, String(item))
      } else {
        url.searchParams.set(key, String(value))
      }
    }
  }
  return url.toString()
}

export async function apiFetch<T>(
  path: string,
  params?: Record<string, unknown>,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(buildUrl(path, params), { cache: "no-store", ...init })
  if (!res.ok) {
    const body = await res.text().catch(() => "")
    throw new ApiError(res.status, body || `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}
