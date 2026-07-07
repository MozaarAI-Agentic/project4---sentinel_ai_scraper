"""Gradio front-end for the SentinelAI Scraper Hugging Face Space.

Two tabs, two different honesty guarantees (see ADR-0017):
- "Guided demo" always works: a curated local fixture with `price`
  deliberately unknown, so every run triggers a real, reproducible
  recovery cycle.
- "Try your own URL" runs the real deterministic pipeline against
  whatever the visitor provides - genuinely useful, but AI-assisted
  recovery on a site we've never seen only works with a real
  ANTHROPIC_API_KEY configured for this Space.
"""

import asyncio
import json
import os
from collections.abc import AsyncIterator
from urllib.parse import urlparse

import gradio as gr
import httpx

API_BASE_URL = "http://localhost:8000"
GUIDED_DEMO_URL = "file:///app/fixtures/demo-sites/static-site/book_page.html"
GUIDED_DEMO_DOMAIN = "demo.sentinelai.local"
POLL_ATTEMPTS = 20
POLL_INTERVAL_SECONDS = 1


def _real_claude_configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


async def _submit_and_poll(url: str, domain: str, required_fields: list[str]) -> AsyncIterator[str]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield "Submitting request..."

        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/jobs",
                json={"url": url, "domain": domain, "required_fields": required_fields},
            )
        except httpx.HTTPError as error:
            yield f"Could not reach the API Gateway: {error}"
            return

        body = response.json()

        if body.get("status") == "success":
            yield f"Extracted immediately, no recovery needed:\n\n{json.dumps(body, indent=2)}"
            return

        if body.get("status") != "recovery_pending":
            yield f"Extraction failed (not recoverable by design - see the Deterministic-First ADR):\n\n{json.dumps(body, indent=2)}"
            return

        job_id = body["job_id"]
        engine_label = (
            "your configured Claude API key (real AI call)"
            if _real_claude_configured()
            else "the demo stand-in engine — no ANTHROPIC_API_KEY configured for this Space, see README"
        )
        yield f"A required selector is missing. Recovery triggered via {engine_label}.\njob_id: {job_id}"

        for attempt in range(1, POLL_ATTEMPTS + 1):
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            poll = await client.get(f"{API_BASE_URL}/api/v1/jobs/{job_id}")
            poll_body = poll.json()
            status = poll_body.get("status")

            if status == "success":
                yield f"Recovered successfully:\n\n{json.dumps(poll_body, indent=2)}"
                return
            if status == "needs_human_review":
                yield f"Recovery exhausted its attempts - flagged for human review:\n\n{json.dumps(poll_body, indent=2)}"
                return

            yield f"Still recovering... (poll {attempt}/{POLL_ATTEMPTS}, status: {status})"

        yield "Timed out waiting for recovery - please try again."


async def run_guided_demo() -> AsyncIterator[str]:
    async for update in _submit_and_poll(GUIDED_DEMO_URL, GUIDED_DEMO_DOMAIN, ["title", "price"]):
        yield update


async def run_custom_url(url: str, fields_csv: str) -> AsyncIterator[str]:
    if not url.strip():
        yield "Please provide a URL."
        return

    fields = [f.strip() for f in fields_csv.split(",") if f.strip()]
    if not fields:
        yield "Please provide at least one required field, comma-separated (e.g. 'title, price')."
        return

    domain = urlparse(url).netloc or "unknown"
    async for update in _submit_and_poll(url, domain, fields):
        yield update


with gr.Blocks(title="SentinelAI Scraper — Live Demo") as demo:
    gr.Markdown(
        """
        # 🛡️ SentinelAI Scraper — Live Demo

        A deterministic-first web extraction platform with AI-powered
        self-healing. Playwright handles every extraction; an AI recovery
        step only fires after a **confirmed** deterministic failure —
        never before, and it never writes to the database directly.

        [Full source, architecture, and 17 ADRs on GitHub](https://github.com/MozaarAI-Agentic/project4---sentinel_ai_scraper)
        """
    )

    with gr.Tab("Guided demo (always works)"):
        gr.Markdown(
            "Runs against a small local fixture page. Its `title` selector "
            "is already known; `price` is deliberately left unknown — so "
            "this always triggers a real, reproducible recovery cycle, "
            "every single time you click the button."
        )
        guided_button = gr.Button("▶ Run guided demo", variant="primary")
        guided_output = gr.Textbox(label="Live status", lines=14)
        guided_button.click(run_guided_demo, outputs=guided_output)

    with gr.Tab("Try your own URL"):
        gr.Markdown(
            "Runs the **real** deterministic pipeline (real Playwright) "
            "against any URL you provide. AI-assisted recovery on a site "
            "this Space has never seen only works if a real "
            "`ANTHROPIC_API_KEY` secret is configured — otherwise a broken "
            "or unknown selector correctly ends up as `needs_human_review`, "
            "which is itself the honest, intended behavior, not a bug."
        )
        url_input = gr.Textbox(label="URL", placeholder="https://books.toscrape.com/")
        fields_input = gr.Textbox(label="Required fields (comma-separated)", placeholder="title")
        custom_button = gr.Button("▶ Run extraction", variant="primary")
        custom_output = gr.Textbox(label="Live status", lines=14)
        custom_button.click(run_custom_url, inputs=[url_input, fields_input], outputs=custom_output)

    gr.Markdown(
        "Recovery engine active for this Space: **"
        + ("real Claude (API key configured)" if _real_claude_configured() else "demo stand-in (no API key configured)")
        + "**"
    )


if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)
