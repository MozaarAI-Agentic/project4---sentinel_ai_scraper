# ADR-0017: Hugging Face Spaces — Simplified Single-Container Deployment

**Status:** Accepted
**Project context:** SentinelAI Scraper

## Context

The GitHub repository's real architecture is 3 microservices + PostgreSQL +
Redis + Prometheus + Grafana, orchestrated by `docker-compose` (ADR-0002,
ADR-0006). Hugging Face Spaces run a **single container** — there is no
docker-compose equivalent. Forcing the real architecture onto a Space
would require either lying about what's running, or quietly gutting the
design this project was built to demonstrate.

A second problem: a public demo that lets any visitor trigger a real,
paid Claude API call would be a cost and abuse risk with no rate limiting
tied to identity.

A third problem: `MockRecoveryEngine` (used in the test suite) returns
placeholder selectors that don't correspond to any real page — pointing a
live demo at an arbitrary URL with the test mock would make "recovery"
visibly fail every time, undermining the exact thing the demo is supposed
to showcase.

## Decision

A separate, clearly-labeled deployment target lives in
`deployment/huggingface-space/`, never touching the core service code:

- **Single container**, all three services run as background processes
  supervised by a small entrypoint script, plus a Gradio UI in the
  foreground on port 7860 (the port HF Spaces expects).
- **SQLite instead of PostgreSQL**, Redis running locally in the same
  container (no separate services to orchestrate).
- **A local fixture page** (reusing `fixtures/demo-sites/static-site/`)
  with the `title` selector pre-seeded and `price` deliberately left
  unseeded at startup — the guided demo always triggers a real,
  reproducible recovery cycle, the same reasoning already applied to the
  test suite (ADR-0012).
- **`DemoRecoveryEngine`** (Space-only code) returns the fixture's real,
  correct selector when asked about `price` — honestly labeled in the UI
  as a demo stand-in, never presented as a live Claude call.
- **Real Claude activates automatically** if `ANTHROPIC_API_KEY` is set as
  a Space secret, reusing the exact same `ClaudeVisionRecoveryEngine` from
  the core codebase (ADR-0016) — no demo-specific AI code path once a key
  exists.
- A second Gradio tab lets visitors run the **real deterministic
  pipeline** (real Playwright) against any URL they provide, with an
  explicit note that AI-assisted recovery on an arbitrary site requires a
  configured key.

## Consequences

### Positive
- The core codebase and its real docker-compose architecture stay
  completely untouched — this is purely additive
- The guided demo is 100% reproducible for every visitor, with zero
  dependency on a third-party site's uptime or structure
- No visitor can spend the owner's Anthropic budget without the owner
  deliberately opting in

### Negative / accepted debt
- `DemoRecoveryEngine` only "knows" the one curated fixture — it is not a
  general-purpose recovery engine, and is clearly out of scope for
  production use
- Single-container process supervision (a shell script) is far less
  robust than real orchestration — acceptable for a demo, not proposed as
  a deployment pattern for the real system

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Point the guided demo at a real external site | Non-reproducible: the demo could break the moment the target site changes its markup — precisely the failure mode this whole project exists to solve, ironically undermining the demo |
| Real Claude on by default for all visitors | Uncontrolled cost exposure to anonymous public traffic |
| Force the full docker-compose stack into one Space via `docker-in-docker` | Unsupported/fragile on HF's infrastructure, and unnecessary complexity for a demo whose only job is to be seen working |

## Recruiter angle

Shows the judgment to build a *deliberately* simplified demo environment
without pretending it's the real production architecture — and to solve
the "public demo shouldn't burn my API budget" problem before it becomes
an incident, not after.
