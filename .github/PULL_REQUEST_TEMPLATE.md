## What does this PR do?

## Which service(s) does it touch?

- [ ] api-gateway
- [ ] extraction-worker
- [ ] recovery-engine
- [ ] sentinel_shared (shared kernel)
- [ ] Documentation only
- [ ] CI/CD / tooling only

## Checklist

- [ ] Tests written first (Red → Green → Refactor), not added after the fact
- [ ] `pytest`, `ruff check`, and `mypy --strict` all pass locally for every service touched
- [ ] New architectural trade-offs are documented as an ADR in `docs/adr/`
- [ ] No new `domain/` dependency on infrastructure (Playwright, Redis, SQLAlchemy, FastAPI)
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
- [ ] `README.md` / `ROADMAP.md` updated if this changes current status or limitations

## Related issue

Closes #

## Notes for the reviewer
