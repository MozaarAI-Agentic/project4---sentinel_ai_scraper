"""Tests du nœud analyze_and_propose.

Chaque nœud LangGraph est testé comme une fonction pure : state en entrée,
dict de mises à jour en sortie. Aucune dépendance à LangGraph lui-même dans
ces tests - seulement à RecoveryEnginePort, via MockRecoveryEngine (Cycle
11). C'est ce qui permet de valider la logique de chaque nœud avant même
d'assembler le graphe complet.
"""

import pytest

from recovery_engine.application.nodes.analyze_and_propose import analyze_and_propose
from recovery_engine.application.recovery_state import RecoveryState
from recovery_engine.infrastructure.mock_recovery_engine import MockRecoveryEngine


def _base_state(**overrides: object) -> RecoveryState:
    state: RecoveryState = {
        "job_id": "job-1",
        "url": "https://books.example/1",
        "domain": "books.example",
        "expected_schema": {"title": str},
        "screenshot_base64": "shot.png",
        "attempt_number": 1,
        "max_attempts": 3,
        "proposed_selectors": None,
        "recovered_data": None,
        "rejection_history": [],
        "validation_result": "pending",
        "final_status": None,
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


class TestAnalyzeAndProposeConfident:
    async def test_populates_proposed_selectors_when_the_engine_is_confident(self) -> None:
        engine = MockRecoveryEngine(seed=7, success_rate=1.0)
        state = _base_state()

        updates = await analyze_and_propose(state, recovery_engine=engine)

        assert updates["proposed_selectors"] is not None
        assert set(updates["proposed_selectors"].keys()) == {"title"}


class TestAnalyzeAndProposeNotConfident:
    async def test_sets_proposed_selectors_to_none_when_the_engine_is_not_confident(self) -> None:
        engine = MockRecoveryEngine(seed=7, success_rate=0.0)
        state = _base_state()

        updates = await analyze_and_propose(state, recovery_engine=engine)

        assert updates["proposed_selectors"] is None


class TestAnalyzeAndProposeRequiresScreenshot:
    async def test_raises_when_screenshot_base64_is_none(self) -> None:
        """Invariant du graphe : ce nœud ne doit s'exécuter qu'après
        capture_screenshot. Une violation ici est un bug d'assemblage du
        graphe, pas un cas métier à absorber silencieusement."""
        engine = MockRecoveryEngine(seed=7, success_rate=1.0)
        state = _base_state(screenshot_base64=None)

        with pytest.raises(ValueError, match="requires a screenshot_base64"):
            await analyze_and_propose(state, recovery_engine=engine)


class TestAnalyzeAndProposeTransmitsRejectionHistory:
    async def test_passes_the_accumulated_rejection_history_to_the_engine(self) -> None:
        received_histories: list[list[str]] = []

        class SpyEngine:
            async def propose_selectors(
                self, screenshot_base64: str, expected_schema: dict[str, type], rejection_history: list[str]
            ):
                received_histories.append(rejection_history)
                return await MockRecoveryEngine(seed=1, success_rate=1.0).propose_selectors(
                    screenshot_base64, expected_schema, rejection_history
                )

        state = _base_state(rejection_history=["attempt 1: selector '.old-title' matched nothing"])

        await analyze_and_propose(state, recovery_engine=SpyEngine())

        assert received_histories == [["attempt 1: selector '.old-title' matched nothing"]]
