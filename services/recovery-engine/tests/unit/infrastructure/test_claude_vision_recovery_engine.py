"""Tests de ClaudeVisionRecoveryEngine.

Utilise un double de test structurel (duck-typing) plutôt qu'un mock du
SDK Anthropic - aucune clé API ni appel réseau réel nécessaire. Ce fichier
teste la construction du prompt, le parsing de la réponse, et surtout la
robustesse face à une sortie IA malformée (JSON invalide, champs
inattendus) - le genre de cas qu'on ne peut pas se permettre de laisser
planter un pipeline de production.
"""

import json
from dataclasses import dataclass, field

from recovery_engine.infrastructure.claude_vision_recovery_engine import (
    ClaudeVisionRecoveryEngine,
)


@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class _FakeUsage:
    input_tokens: int = 100
    output_tokens: int = 50


@dataclass
class _FakeAnthropicResponse:
    content: list[_FakeTextBlock]
    usage: _FakeUsage = field(default_factory=_FakeUsage)


class _FakeMessages:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.last_call_kwargs: dict[str, object] | None = None

    async def create(self, **kwargs: object) -> _FakeAnthropicResponse:
        self.last_call_kwargs = kwargs
        return _FakeAnthropicResponse(content=[_FakeTextBlock(text=self._response_text)])


class _FakeAnthropicClient:
    def __init__(self, response_text: str) -> None:
        self.messages = _FakeMessages(response_text)


class TestClaudeVisionRecoveryEngineConfidentProposal:
    async def test_returns_a_confident_proposal_from_valid_json(self) -> None:
        client = _FakeAnthropicClient(response_text=json.dumps({"title": "h1.title"}))
        engine = ClaudeVisionRecoveryEngine(client=client)  # type: ignore[arg-type]

        proposal = await engine.propose_selectors(
            screenshot_base64="aGVsbG8=", expected_schema={"title": str}, rejection_history=[]
        )

        assert proposal.is_confident is True
        assert proposal.selectors == {"title": "h1.title"}

    async def test_sends_the_screenshot_as_a_base64_image_block(self) -> None:
        client = _FakeAnthropicClient(response_text=json.dumps({"title": "h1"}))
        engine = ClaudeVisionRecoveryEngine(client=client)  # type: ignore[arg-type]

        await engine.propose_selectors(
            screenshot_base64="aGVsbG8=", expected_schema={"title": str}, rejection_history=[]
        )

        call_kwargs = client.messages.last_call_kwargs
        assert call_kwargs is not None
        image_block = call_kwargs["messages"][0]["content"][0]  # type: ignore[index]
        assert image_block["type"] == "image"
        assert image_block["source"]["data"] == "aGVsbG8="


class TestClaudeVisionRecoveryEngineMalformedOutput:
    """Claude peut ignorer la consigne de format - ces cas ne doivent
    jamais faire planter le graphe de recovery, seulement produire une
    non-confiance, cohérent avec le contrat de RecoveryEnginePort."""

    async def test_returns_not_confident_when_the_response_is_not_valid_json(self) -> None:
        client = _FakeAnthropicClient(response_text="Sure! Here are the selectors: h1.title")
        engine = ClaudeVisionRecoveryEngine(client=client)  # type: ignore[arg-type]

        proposal = await engine.propose_selectors(
            screenshot_base64="aGVsbG8=", expected_schema={"title": str}, rejection_history=[]
        )

        assert proposal.is_confident is False
        assert proposal.selectors == {}

    async def test_ignores_selectors_for_fields_that_were_not_requested(self) -> None:
        client = _FakeAnthropicClient(
            response_text=json.dumps({"title": "h1.title", "unexpected_field": ".foo"})
        )
        engine = ClaudeVisionRecoveryEngine(client=client)  # type: ignore[arg-type]

        proposal = await engine.propose_selectors(
            screenshot_base64="aGVsbG8=", expected_schema={"title": str}, rejection_history=[]
        )

        assert proposal.selectors == {"title": "h1.title"}

    async def test_returns_not_confident_when_json_is_valid_but_not_an_object(self) -> None:
        client = _FakeAnthropicClient(response_text=json.dumps(["h1.title", ".price"]))
        engine = ClaudeVisionRecoveryEngine(client=client)  # type: ignore[arg-type]

        proposal = await engine.propose_selectors(
            screenshot_base64="aGVsbG8=", expected_schema={"title": str}, rejection_history=[]
        )

        assert proposal.is_confident is False

    async def test_returns_not_confident_when_all_proposed_values_are_the_wrong_type(self) -> None:
        client = _FakeAnthropicClient(response_text=json.dumps({"title": 123}))
        engine = ClaudeVisionRecoveryEngine(client=client)  # type: ignore[arg-type]

        proposal = await engine.propose_selectors(
            screenshot_base64="aGVsbG8=", expected_schema={"title": str}, rejection_history=[]
        )

        assert proposal.is_confident is False


class TestClaudeVisionRecoveryEngineRejectionHistory:
    async def test_includes_rejection_history_in_the_prompt(self) -> None:
        client = _FakeAnthropicClient(response_text=json.dumps({"title": "h1.title"}))
        engine = ClaudeVisionRecoveryEngine(client=client)  # type: ignore[arg-type]

        await engine.propose_selectors(
            screenshot_base64="aGVsbG8=",
            expected_schema={"title": str},
            rejection_history=["attempt 1: selector '.old-title' matched nothing"],
        )

        call_kwargs = client.messages.last_call_kwargs
        assert call_kwargs is not None
        user_text_block = call_kwargs["messages"][0]["content"][1]  # type: ignore[index]
        assert "attempt 1" in user_text_block["text"]


class TestClaudeVisionRecoveryEngineCostTracking:
    async def test_records_a_cost_based_on_real_token_usage(self) -> None:
        from sentinel_shared.observability.metrics import AI_RECOVERY_COST_USD_TOTAL

        client = _FakeAnthropicClient(response_text=json.dumps({"title": "h1.title"}))
        engine = ClaudeVisionRecoveryEngine(client=client)  # type: ignore[arg-type]

        before = AI_RECOVERY_COST_USD_TOTAL._value.get()
        await engine.propose_selectors(
            screenshot_base64="aGVsbG8=", expected_schema={"title": str}, rejection_history=[]
        )
        after = AI_RECOVERY_COST_USD_TOTAL._value.get()

        assert after > before
