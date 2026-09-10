// Typed fetch wrapper for tasko-core.
//
// Runs on both sides of the SSR boundary:
//  - server (SSR prefetch): TASKO_CORE_URL, the internal address (e.g.
//    http://core:8000 on the compose network).
//  - browser: NEXT_PUBLIC_TASKO_CORE_URL if set (baked at build time), else
//    the page's own origin — so a same-origin reverse-proxy deploy (Traefik &
//    co. serving /api and /ws on the dashboard host) needs no build-time
//    config. Only set NEXT_PUBLIC_TASKO_CORE_URL when the API lives on a
//    different origin than the dashboard.

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
  if (typeof window === "undefined") {
    return process.env.TASKO_CORE_URL ?? "http://localhost:8000"
  }
  // `||` not `??`: an empty NEXT_PUBLIC_TASKO_CORE_URL (the default build arg)
  // also falls through to the current origin.
  return process.env.NEXT_PUBLIC_TASKO_CORE_URL || window.location.origin
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
