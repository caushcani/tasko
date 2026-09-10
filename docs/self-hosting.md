# Self-hosting Tasko

Three ways to run it, least to most exposed. Pick one.

> **Tasko has no built-in authentication.** Anyone who can reach the dashboard
> or the API can see every task payload, worker, and queue on your fleet, and
> can create/delete alert rules. Only the LAN options below are safe as-is;
> public exposure **must** be paired with proxy-level auth (covered under
> Traefik).

## 1. Local / LAN

The base stack at `docker/docker-compose.yml` is the dev stack — source is
bind-mounted, both apps hot-reload, and it publishes to the host so you can
reach it:

| Service  | Host port | |
|----------|-----------|--|
| web      | `3100`    | the dashboard |
| core     | `8100`    | the API |
| postgres | `5434`    | for DBeaver etc. |

```bash
docker compose -f docker/docker-compose.yml up --build
docker compose -f docker/docker-compose.yml exec core tasko-seed   # sample data
```

`redis` stays on the compose network only. Ports bind to `0.0.0.0` — fine on a
trusted LAN, but if the machine is on an untrusted network, restrict them:

```yaml
# docker/docker-compose.override.yml   (compose picks this up automatically)
services:
  web:      { ports: !override ["127.0.0.1:3100:3000"] }
  core:     { ports: !override ["127.0.0.1:8100:8000"] }
  postgres: { ports: !override [] }
```

Then reach it over an SSH tunnel: `ssh -L 3100:localhost:3100 your-host`.

## 2. Production-style, still local

`docker-compose.prod.yml` overlays the base: built images, no bind-mounts,
`restart: unless-stopped`. Still publishes the same host ports.

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up --build -d
```

Reference only — a real deployment supplies its own database URL and secrets
in `tasko.docker.yaml` rather than the `tasko:tasko` compose defaults.

## 3. Public, behind Traefik

For anyone already running [Traefik](https://doc.traefik.io/traefik/) as their
reverse proxy. `docker/docker-compose.traefik.yml` overlays the base: it builds
the immutable images, **drops every published host port** (Traefik is the only
ingress), and serves the dashboard and the API on **one origin** — so the
browser bundle needs no build-time URL and there's no CORS to configure.

### Prerequisites

- A running Traefik with a cert resolver (e.g. `letsencrypt`) and an
  entrypoint named `websecure` (:443) — the standard setup.
- An external docker network your Traefik is attached to (commonly `traefik`).
- `htpasswd` (`apache2-utils` / `httpd-tools`).

### Configure

```bash
cp .env.example .env
```

Fill in `.env` (repo root):

```ini
TASKO_DOMAIN=tasko.yourdomain.com
TRAEFIK_CERTRESOLVER=letsencrypt
TRAEFIK_NETWORK=traefik

# REQUIRED. Double every '$' so compose doesn't treat it as interpolation:
#   htpasswd -nbB admin 'your-password' | sed -e 's/\$/\$\$/g'
TASKO_BASICAUTH_USERS=admin:$$2y$$05$$abcdefghijklmnopqrstuv...

POSTGRES_PASSWORD=something-real
```

With `TASKO_BASICAUTH_USERS` empty, Traefik rejects every request — Tasko
never comes up unauthenticated.

### Run

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.traefik.yml up -d --build
docker compose -f docker/docker-compose.yml -f docker/docker-compose.traefik.yml exec core tasko-seed
```

Tasko is now at `https://tasko.yourdomain.com`, behind basicauth, TLS from
your cert resolver. The overlay wires:

- `Host(tasko.yourdomain.com)` → the dashboard (`web`, :3000)
- `... && (PathPrefix(/api) || PathPrefix(/ws))` → the API + websocket
  (`core`, :8000), higher priority so it wins
- the `tasko-auth` basicauth middleware on both

### Split onto separate subdomains (optional)

If you'd rather serve the API from `api.tasko.yourdomain.com`:

1. Change the `core` router rule in the overlay to `Host(`api.tasko...`)` and
   drop the `PathPrefix`.
2. Build the web image with the API URL baked in:
   `--build-arg NEXT_PUBLIC_TASKO_CORE_URL=https://api.tasko.yourdomain.com`.
3. The browser is now cross-origin, so add both hosts to `server.cors_origins`
   in `tasko.docker.yaml`:
   ```yaml
   server:
     cors_origins:
       - https://tasko.yourdomain.com
       - https://api.tasko.yourdomain.com
   ```

The single-origin default avoids all three steps.

## Summary

| Setup | Reachable from | Auth |
|---|---|---|
| Base compose | LAN via the published ports | none — trusted network |
| Base + `127.0.0.1` port override | localhost / SSH tunnel | none — trusted network |
| Base + prod overlay | LAN via the published ports | none — trusted network |
| Base + Traefik overlay | public internet, TLS | **basicauth, enforced** |
