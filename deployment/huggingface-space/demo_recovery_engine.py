"""Demo stand-in for Claude, used by the Hugging Face Space ONLY when no
ANTHROPIC_API_KEY secret is configured (see ADR-0017). Lives entirely
outside the core `recovery_engine` package - this is demo-specific glue
code, never mixed into the production codebase.

It knows exactly one thing: the correct selectors for the curated fixture
page used in the guided demo tab. The Gradio UI always labels which
engine actually produced a recovery, so this is never silently presented
as a real AI call.
"""

from recovery_engine.domain.value_objects import SelectorProposal

# Matches the real markup in fixtures/demo-sites/static-site/book_page.html
_KNOWN_SELECTORS = {
    "title": "h1.title",
    "price": "span.price",
}


class DemoRecoveryEngine:
    async def propose_selectors(
        self,
        screenshot_base64: str,
        expected_schema: dict[str, type],
        rejection_history: list[str],
    ) -> SelectorProposal:
        selectors = {
            field_name: _KNOWN_SELECTORS[field_name]
            for field_name in expected_schema
            if field_name in _KNOWN_SELECTORS
        }
        if not selectors:
            return SelectorProposal(is_confident=False, selectors={})
        return SelectorProposal(is_confident=True, selectors=selectors)
