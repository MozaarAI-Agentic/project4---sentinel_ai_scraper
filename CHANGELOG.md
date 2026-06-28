# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project
will adopt [Semantic Versioning](https://semver.org/) starting with its
first tagged release (see [ROADMAP.md](ROADMAP.md)).

## [Unreleased]

Everything below was built incrementally, TDD-first, across the MVP
build. No version has been tagged yet — this is the state of `main`.

### Added

**Extraction Worker**
- Domain layer: `ExtractionValidator`, `ExtractionOutcome`, `Selector` entity, `BrowserPort` / `SelectorRepositoryPort` contracts
- `ExtractDataUseCase` with candidate-selector override support (used by recovery validation)
- `PlaywrightBrowser` — real Chromium-backed extraction and screenshot capture
- `RedisPostgresSelectorRepository` — cache-aside selector storage (ADR-0007)
- HTTP interface: `POST /internal/extract`, `POST /internal/screenshot`, `POST /internal/selectors`
- Prometheus instrumentation: extraction duration/result, cache hit/miss

**API Gateway**
- `Job` entity with explicit state transitions, `RecoveryDecisionPolicy` (not every failure warrants AI escalation)
- `ProcessScrapeRequestUseCase` implementing the hybrid sync/async model (ADR-0003)
- `HttpExtractionService`, `SqlAlchemyJobRepository`, `RedisRecoveryQueue` — real infrastructure adapters
- HTTP interface: `POST /api/v1/jobs`, `GET /api/v1/jobs/{id}`
- Prometheus instrumentation: job status counter

**Recovery Engine**
- `MockRecoveryEngine` with seed-configurable reproducibility (ADR-0012)
- Full LangGraph recovery graph: `capture_screenshot → analyze_and_propose → validate_selectors_live → decide_next_step → persist_selector / escalate_human`
- `handle_no_confident_proposal` node, added after a graph-assembly test revealed a routing gap not visible in isolated node tests
- `RecoveryQueueConsumer` — closes the loop from Redis queue to Job update
- Prometheus instrumentation: recovery attempt outcome, recovery duration, simulated AI cost

**Shared kernel (`sentinel_shared`)**
- `FailureReason`, `JobStatus` enums
- `ExtractionValidator`, `ExtractionOutcome`, `Job` — migrated from service-local code once genuine cross-service duplication was identified
- `observability/metrics.py` — consistent Prometheus metric definitions across all three services

**Documentation**
- 12 ADRs covering every non-trivial architectural trade-off
- C4 context and container diagrams, sequence diagrams, LangGraph state diagram — all derived from the actual implemented code
- Testing strategy document with measured (not estimated) coverage
- Observability catalogue mapping product KPIs to instrumented metrics

### Known limitations (tracked, not hidden)
- Claude Computer Use is mocked; real integration is a scoped next step
- No authentication on the API (ADR-0009)
- No distributed tracing (Prometheus metrics only)
- No Docker Compose / CI pipeline yet
- Recovery queue can lose a message if the consumer crashes mid-processing (`BRPOP`, no ack)

[Unreleased]: https://github.com/your-username/sentinelai-scraper/compare/main
