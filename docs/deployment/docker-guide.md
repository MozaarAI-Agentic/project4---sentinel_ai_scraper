# Docker Guide

## Honesty note

Here's the precise, tested truth rather than a vague disclaimer: **the
Docker daemon genuinely runs** in the sandbox this project was built in
(`dockerd` starts, `docker info` responds correctly, overlayfs storage
driver initializes without error). But **pulling any base image fails**
(`docker pull python:3.12-slim` → `403 Forbidden` on
`registry-1.docker.io`) — this development environment's network egress
is allow-listed to specific domains (PyPI, npm, GitHub, a few package
registries) and Docker Hub isn't one of them.

So the honest status is: Docker itself isn't the blocker, a network
policy outside my control is. Every Dockerfile and the compose file were
written and statically reviewed with full care (dependency lists
cross-checked against real imports, YAML validated), but the very first
`docker compose up --build` on a machine with normal internet access is
still the real test — not a formality, but also not starting from zero.

## Prerequisites

- Docker Engine 24+
- Docker Compose v2 (`docker compose`, not the legacy `docker-compose`)

## Quickstart

```bash
cd infra
cp .env.example .env
# edit .env - at minimum, change POSTGRES_PASSWORD

docker compose up --build
```

This starts, in order (thanks to `depends_on` + healthchecks):
1. PostgreSQL and Redis
2. Extraction Worker (needs both to be healthy)
3. API Gateway and Recovery Engine (need the Worker to be healthy too)
4. Prometheus (scrapes all three services' `/metrics`)
5. Grafana (`http://localhost:3000`, default login `admin` / `admin`)

## Exposed ports

| Service | Port | Purpose |
|---|---|---|
| API Gateway | `8000` | Public API (`POST /api/v1/jobs`, `GET /api/v1/jobs/{id}`) |
| Extraction Worker | `8001` | Internal API (not meant for external clients) |
| Recovery Engine | `8002` | Sidecar only (`/health`, `/metrics`) — its real work happens via the Redis queue, not HTTP |
| PostgreSQL | `5432` | Exposed for local debugging/inspection only |
| Redis | `6379` | Same |
| Prometheus | `9090` | Metrics UI |
| Grafana | `3000` | Dashboards |

## Why the Extraction Worker's image is built differently

Its `Dockerfile` uses a single stage, not multi-stage like the other two
services. Playwright's `--with-deps` installation pulls in system-level
libraries (`libnss3`, `libatk`, etc.) that don't copy cleanly across
Docker build stages without careful, individually-verified `COPY`
instructions — something this environment couldn't validate against a
real daemon. The trade-off (a larger image) is documented, not hidden; see
the [ADR directory](../adr/) and [ROADMAP.md](../../ROADMAP.md) for the
multi-stage optimization tracked as future work.

## Why the Recovery Engine's `CMD` is different

`services/recovery-engine/Dockerfile` runs `python -m recovery_engine.main`,
not `uvicorn` directly. This service does two things at once — serves a
thin HTTP sidecar (`/health`, `/metrics`) **and** continuously consumes
the Redis recovery queue — both in the same asyncio process (see
`main.py`). Running `uvicorn` alone would start the sidecar but never
process a single recovery job.

## Verifying it actually works

```bash
# Nominal path
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"url": "https://books.toscrape.com/", "domain": "books.toscrape.com", "required_fields": ["title"]}'

# Metrics
curl http://localhost:8000/metrics
curl http://localhost:8002/health
```

## Known gaps in this deployment setup

- No TLS termination (add a reverse proxy — Traefik or nginx — before any
  real exposure)
- No secrets manager — `.env` is fine for local dev, not for production
- No resource limits (`mem_limit`, `cpus`) set on any service yet
- Prometheus/Grafana have no persistent volume configured for their own
  data — a `docker compose down` loses dashboard customizations
