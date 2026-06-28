# Contributing to SentinelAI Scraper

Thanks for considering contributing. This project was built with a fairly
strict discipline (strict TDD, Ruff + MyPy strict on every change, ADRs
for every architectural decision) — the goal here is to keep that bar,
not to gatekeep casual contributions.

## Before you start

- Check open issues first — someone might already be working on it.
- For anything beyond a small fix (new feature, architectural change),
  open an issue to discuss the approach before writing code. It's a lot
  less frustrating than a PR getting reshaped in review.

## Development workflow

This repo follows strict **Red → Green → Refactor** TDD:

1. Write a failing test first.
2. Write the minimal code to make it pass.
3. Refactor with the safety net of the now-passing test.

Every service has the same internal structure
(`domain/ → application/ → infrastructure/ → interfaces/`). The `domain/`
layer must never import Playwright, Redis, SQLAlchemy, or FastAPI — if
your change needs to, it probably belongs in a different layer.

### Running the checks locally

```bash
export PYTHONPATH=src:../../libs/sentinel_shared/src

# Tests
python -m pytest tests/ -v

# Lint
ruff check src/ tests/ --line-length 100

# Strict type checking
mypy src/<package_name>/ --strict --ignore-missing-imports
```

All three must be clean before opening a PR. There are currently 114
tests across the monorepo, all passing, with zero Ruff or MyPy warnings —
that's the bar to maintain, not exceed with more churn than necessary.

## Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(recovery-engine): add handle_no_confident_proposal routing node
fix(api-gateway): correct eager Depends() resolution blocking startup
docs(adr): add ADR-0012 on seed-based mock reproducibility
test(worker): add contract test for unknown failure_reason
refactor(shared): migrate ExtractionValidator to sentinel_shared
```

Types used in this repo: `feat`, `fix`, `docs`, `test`, `refactor`,
`chore`, `perf`. Scope is the service or module touched.

## Architecture Decision Records

If your change involves a real trade-off (not just an implementation
detail), add an ADR in `docs/adr/` following the existing template. A
good rule of thumb: if you'd need to defend the choice in a code review or
an interview, it deserves an ADR.

## Pull Request checklist

- [ ] Tests written first, following Red → Green → Refactor
- [ ] `pytest`, `ruff check`, and `mypy --strict` all pass locally
- [ ] New architectural decisions documented as an ADR
- [ ] No new `domain/` dependency on infrastructure
- [ ] Commit messages follow Conventional Commits

## Questions

Open a GitHub issue — for a solo-maintained project, that's the fastest
way to get a response.
