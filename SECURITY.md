# Security Policy

## Supported Versions

This project is pre-1.0 and under active development. Security fixes are
applied to `main` only — there's no LTS branch yet.

| Version | Supported |
|---|---|
| `main` (unreleased) | ✅ |

## Reporting a Vulnerability

If you find a security issue, please **do not open a public GitHub
issue**. Instead, use GitHub's private vulnerability reporting (Security
tab → "Report a vulnerability") or contact the maintainer directly through
their GitHub profile.

Please include:
- A description of the vulnerability and its potential impact
- Steps to reproduce
- Any suggested mitigation, if you have one

You can expect an initial response within a few days. This is currently a
solo-maintained project, so please bear with response times outside of
that.

## Current Security Posture — Read This Before Deploying Anywhere Public

This is an honest account of where things stand, not a marketing page.

### What's in place

- **No secrets in code.** All configuration (`DATABASE_URL`, `REDIS_URL`,
  `EXTRACTION_WORKER_BASE_URL`) is read from environment variables, never
  hardcoded.
- **Input validation at every HTTP boundary** via Pydantic — malformed
  requests are rejected before reaching business logic.
- **Structural contract-break protection.** If one service sends another
  a value it doesn't recognize (e.g. an unknown `failure_reason`), the
  receiving service treats it as an infrastructure failure rather than
  crashing on an unhandled exception.

### What's explicitly NOT in place yet

- **No authentication on the API.** This is a deliberate, documented MVP
  decision (see [ADR-0009](docs/adr/0009-no-authentication-mvp.md)), not
  an oversight. Compensating controls (rate limiting, restricted network
  binding) are designed but rate limiting isn't implemented in code yet.
  **Do not expose this API publicly without adding authentication first.**
- **No automated dependency scanning yet.** Dependabot configuration is
  planned (see [ROADMAP.md](ROADMAP.md)) but not yet active.
- **No hardened Docker images yet.** Dockerfiles don't exist yet
  (Phase 12 — Deployment, in progress). Once they do, they'll run as a
  non-root user with minimal base images — but that's a statement of
  intent, not a completed fact, until it lands.
- **Playwright/Chromium runs with default sandboxing.** No custom seccomp
  profile or additional container hardening has been applied yet.

If you're evaluating this project for anything beyond local development
or a portfolio review, treat the items above as blockers, not nice-to-haves.

## Dependency Management

Once Dependabot is configured (tracked in the roadmap), security patches
for dependencies will be reviewed and merged promptly. Until then,
dependency versions should be checked manually before any production use.
