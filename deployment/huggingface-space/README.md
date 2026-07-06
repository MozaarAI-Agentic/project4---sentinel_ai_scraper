---
title: SentinelAI Scraper
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# SentinelAI Scraper — Live Demo

This Space runs a **deliberately simplified** version of
[SentinelAI Scraper](https://github.com/your-username/sentinelai-scraper):
a deterministic-first web extraction platform where Playwright does the
work and an AI recovery step only fires after a confirmed deterministic
failure.

## What's different from the real architecture

Hugging Face Spaces run a single container — there's no docker-compose
here. This Space packs all three microservices into one container with
SQLite instead of PostgreSQL, and a curated local fixture for the guided
demo instead of an arbitrary live site (so it's reproducible for every
visitor, not dependent on some external site's uptime). The full
reasoning is in [ADR-0017](https://github.com/your-username/sentinelai-scraper/blob/main/docs/adr/0017-huggingface-space-simplified-deployment.md).

## About the AI recovery step

By default, this Space uses a small stand-in that only knows the
answer for the one curated demo fixture — it is **not** a real Claude
API call, and the UI always tells you which one just ran. If you fork
this Space and set your own `ANTHROPIC_API_KEY` secret, it automatically
switches to the real `ClaudeVisionRecoveryEngine` from the core codebase
— no code changes required.

## Try it

- **Guided demo** tab: always works, always triggers a real recovery cycle
- **Try your own URL** tab: runs the real deterministic pipeline against
  any site you provide

[Full source, 17 ADRs, 140 tests, and the real production architecture on GitHub](https://github.com/your-username/sentinelai-scraper)
