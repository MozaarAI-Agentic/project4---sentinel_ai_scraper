"""Tests de decide_next_step.

Contrairement aux autres nœuds, cette fonction ne retourne PAS un dict de
mises à jour du state - c'est une fonction de routage pure destinée à
`add_conditional_edges` de LangGraph, qui retourne le nom du nœud suivant.
"""

from recovery_engine.application.nodes.decide_next_step import decide_next_step
from recovery_engine.application.recovery_state import RecoveryState


def _base_state(**overrides: object) -> RecoveryState:
    state: RecoveryState = {
        "job_id": "job-1",
        "url": "https://books.example/1",
        "domain": "books.example",
        "expected_schema": {"title": str},
        "screenshot_base64": "aGVsbG8=",
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


class TestDecideNextStepValid:
    def test_routes_to_persist_selector_when_validation_is_valid(self) -> None:
        state = _base_state(validation_result="valid")

        assert decide_next_step(state) == "persist_selector"


class TestDecideNextStepInvalidWithAttemptsRemaining:
    def test_routes_back_to_analyze_and_propose_when_attempts_remain(self) -> None:
        state = _base_state(validation_result="invalid", attempt_number=2, max_attempts=3)

        assert decide_next_step(state) == "analyze_and_propose"


class TestDecideNextStepInvalidMaxAttemptsReached:
    def test_routes_to_escalate_human_when_no_attempts_remain(self) -> None:
        state = _base_state(validation_result="invalid", attempt_number=4, max_attempts=3)

        assert decide_next_step(state) == "escalate_human"

    def test_routes_to_escalate_human_exactly_at_the_boundary(self) -> None:
        """attempt_number == max_attempts + 1 après incrémentation par
        validate_selectors_live signifie que toutes les tentatives autorisées
        ont été consommées."""
        state = _base_state(validation_result="invalid", attempt_number=4, max_attempts=3)

        assert decide_next_step(state) == "escalate_human"
