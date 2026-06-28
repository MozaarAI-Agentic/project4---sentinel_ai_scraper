# Roadmap

This roadmap is organized by horizon, not by priority within each horizon
— near-term items are what's needed to consider the project genuinely
production-ready; mid-term items are real engineering value-adds; long-term
items are where this could go if it became an actual product rather than a
portfolio piece.

## Near-term (next up)

- [ ] Dockerize all three services + `docker-compose.yml` for one-command local startup *(Dockerfiles + compose written and statically reviewed; blocked on Docker Hub registry access in the dev sandbox - see docs/deployment/docker-guide.md)*
- [ ] GitHub Actions CI: lint (Ruff), strict type-check (MyPy), test on every push
- [ ] Pre-commit hooks mirroring the CI checks
- [x] ~~Activate real Claude Computer Use behind the existing `RecoveryEnginePort`~~ — done via `ClaudeVisionRecoveryEngine` (vision + structured output, not the literal Computer Use tool - see ADR-0016)
- [x] ~~Contract tests between API Gateway ↔ Extraction Worker ↔ Recovery Engine~~ — done, `tests/contract/` (6 tests)
- [x] ~~Rate limiting middleware on `POST /api/v1/jobs`~~ — done, Redis fixed-window limiter

## Mid-term (real engineering value)

- [x] ~~OpenTelemetry trace propagation across the async recovery path~~ — done, trace context injected into Redis Stream fields, verified end-to-end
- [x] ~~Migrate the recovery queue from a plain Redis list to Redis Streams~~ — done (ADR-0014), consumer group + XACK + XAUTOCLAIM, crash scenario proven by test
- [ ] API Key or OAuth2 authentication, replacing the current no-auth MVP posture (ADR-0009)
- [ ] Browser pool manager for Playwright — currently a fresh Chromium instance launches per extraction; pooling would matter once latency is measured under real load
- [ ] Unit of Work pattern if multi-entity transactions become necessary (not needed yet — deliberately not built ahead of a real requirement)
- [ ] Typed `NodeError` for LangGraph invariant violations, distinguishable from ordinary recovery failures in monitoring
- [ ] Automated dependency scanning (Dependabot) and secret scanning
- [ ] Selector version rollback — currently only the active version is queryable; full history exists in Postgres but isn't exposed via any endpoint
- [ ] Real OTLP exporter (Jaeger/Tempo) replacing the default `ConsoleSpanExporter`
- [ ] Automated `reclaim_stale_messages()` invocation (currently must be called explicitly - not scheduled)

## Long-term (if this became a real product)

- [ ] Multi-tenant SaaS architecture with per-tenant selector isolation and usage-based billing
- [ ] Web dashboard (beyond the raw API) for non-technical users to configure scrape targets
- [ ] Config-driven "site profile" library so onboarding a new target site doesn't require any code change
- [ ] Database-per-service migration with event sourcing (Debezium/Kafka), once genuine multi-service data ownership conflicts are measured, not assumed
- [ ] Fine-tuned lightweight vision model for simple, high-frequency recovery cases, reserving Claude Computer Use for genuinely ambiguous ones
- [ ] Outbound webhooks (HMAC-signed) as an alternative to polling for recovery completion
- [ ] Dead-letter handling for jobs that repeatedly fail recovery, with a dedicated triage view

## Documentation & tooling improvements

- [ ] Auto-generate sequence diagrams from real OpenTelemetry traces once tracing lands, so diagrams can never silently drift from actual behavior
- [ ] CI check that fails the build if a code comment references an ADR number that doesn't exist in `docs/adr/`
- [ ] Cookiecutter template scaffolding a new microservice with the existing Clean Architecture layout, if the number of services grows
