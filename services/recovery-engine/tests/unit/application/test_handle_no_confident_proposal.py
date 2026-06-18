"""Tests de handle_no_confident_proposal.

Comble un vrai trou de routage découvert à l'assemblage du graphe : si
analyze_and_propose n'est pas confiant, on ne peut pas router vers
validate_selectors_live (qui suppose des sélecteurs non-None). Ce nœud
traite l'absence de proposition exactement comme un rejet - même
comptabilité de tentatives, même historique - pour que decide_next_step
puisse être réutilisé sans dupliquer sa logique de routage.
"""

from recovery_engine.application.nodes.handle_no_confident_proposal import (
    handle_no_confident_proposal,
)
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


class TestHandleNoConfidentProposal:
    def test_marks_validation_result_as_invalid(self) -> None:
        state = _base_state()

        updates = handle_no_confident_proposal(state)

        assert updates["validation_result"] == "invalid"

    def test_increments_attempt_number(self) -> None:
        state = _base_state(attempt_number=2)

        updates = handle_no_confident_proposal(state)

        assert updates["attempt_number"] == 3

    def test_appends_a_rejection_reason(self) -> None:
        state = _base_state(attempt_number=1, rejection_history=["previous entry"])

        updates = handle_no_confident_proposal(state)

        assert updates["rejection_history"] == [
            "previous entry",
            "attempt 1: no confident proposal from the recovery engine",
        ]
