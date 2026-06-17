"""Tests de MockRecoveryEngine.

Réconciliation décidée en Phase 7 : un `seed` fixe rend le comportement
"aléatoire" parfaitement déterministe et reproductible (utilisé en CI et
pour rejouer un scénario de démo précis) ; son absence donne une variance
réaliste pour l'exploration manuelle. C'est la fondation sur laquelle tout
le graphe LangGraph du Recovery Engine va s'appuyer.
"""

from recovery_engine.domain.value_objects import SelectorProposal
from recovery_engine.infrastructure.mock_recovery_engine import MockRecoveryEngine


class TestMockRecoveryEngineDeterminismWithSeed:
    async def test_same_seed_produces_the_same_sequence_of_outcomes(self) -> None:
        engine_a = MockRecoveryEngine(seed=42, success_rate=0.5)
        engine_b = MockRecoveryEngine(seed=42, success_rate=0.5)

        results_a = [
            (await engine_a.propose_selectors(
                screenshot_base64="shot.png", expected_schema={"title": str}, rejection_history=[]
            )).is_confident
            for _ in range(20)
        ]
        results_b = [
            (await engine_b.propose_selectors(
                screenshot_base64="shot.png", expected_schema={"title": str}, rejection_history=[]
            )).is_confident
            for _ in range(20)
        ]

        assert results_a == results_b

    async def test_different_seeds_can_produce_different_sequences(self) -> None:
        engine_a = MockRecoveryEngine(seed=1, success_rate=0.5)
        engine_b = MockRecoveryEngine(seed=2, success_rate=0.5)

        results_a = [
            (await engine_a.propose_selectors(
                screenshot_base64="shot.png", expected_schema={"title": str}, rejection_history=[]
            )).is_confident
            for _ in range(20)
        ]
        results_b = [
            (await engine_b.propose_selectors(
                screenshot_base64="shot.png", expected_schema={"title": str}, rejection_history=[]
            )).is_confident
            for _ in range(20)
        ]

        assert results_a != results_b


class TestMockRecoveryEngineSuccessRateExtremes:
    async def test_success_rate_zero_never_proposes_a_confident_selector(self) -> None:
        engine = MockRecoveryEngine(seed=7, success_rate=0.0)

        for _ in range(10):
            proposal = await engine.propose_selectors(
                screenshot_base64="shot.png", expected_schema={"title": str}, rejection_history=[]
            )
            assert proposal.is_confident is False

    async def test_success_rate_one_always_proposes_a_confident_selector(self) -> None:
        engine = MockRecoveryEngine(seed=7, success_rate=1.0)

        for _ in range(10):
            proposal = await engine.propose_selectors(
                screenshot_base64="shot.png", expected_schema={"title": str}, rejection_history=[]
            )
            assert proposal.is_confident is True


class TestMockRecoveryEngineProposalContent:
    async def test_confident_proposal_includes_a_selector_for_each_expected_field(self) -> None:
        engine = MockRecoveryEngine(seed=7, success_rate=1.0)

        proposal = await engine.propose_selectors(
            screenshot_base64="shot.png",
            expected_schema={"title": str, "price": str},
            rejection_history=[],
        )

        assert set(proposal.selectors.keys()) == {"title", "price"}

    async def test_non_confident_proposal_has_no_selectors(self) -> None:
        engine = MockRecoveryEngine(seed=7, success_rate=0.0)

        proposal = await engine.propose_selectors(
            screenshot_base64="shot.png", expected_schema={"title": str}, rejection_history=[]
        )

        assert proposal.selectors == {}


class TestMockRecoveryEngineCostMetric:
    """Le mock simule un coût fixe par appel (Phase 10) - la même
    instrumentation servira à ClaudeRecoveryEngine (coût réel) sans
    changer le point de mesure côté graphe."""

    async def test_records_a_simulated_cost_per_call(self) -> None:
        from sentinel_shared.observability.metrics import AI_RECOVERY_COST_USD_TOTAL

        engine = MockRecoveryEngine(seed=7, success_rate=1.0)

        before = AI_RECOVERY_COST_USD_TOTAL._value.get()
        await engine.propose_selectors(
            screenshot_base64="shot.png", expected_schema={"title": str}, rejection_history=[]
        )
        after = AI_RECOVERY_COST_USD_TOTAL._value.get()

        assert after > before


class TestSelectorProposalIsImmutable:
    def test_cannot_mutate_a_proposal_after_creation(self) -> None:
        proposal = SelectorProposal(is_confident=True, selectors={"title": "h1"})

        with __import__("pytest").raises(Exception):
            proposal.is_confident = False  # type: ignore[misc]
