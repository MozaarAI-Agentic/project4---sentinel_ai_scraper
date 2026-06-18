"""Nœud LangGraph : traite l'absence de proposition confiante de l'IA.

Découvert nécessaire à l'assemblage du graphe (Cycle 15) : sans ce nœud,
un analyze_and_propose non confiant routerait vers validate_selectors_live,
qui suppose des sélecteurs non-None et planterait. Ce nœud traite l'absence
de proposition exactement comme un rejet - même comptabilité de tentatives,
même historique - pour réutiliser decide_next_step sans dupliquer sa
logique de routage.
"""

from typing import Any

from recovery_engine.application.recovery_state import RecoveryState


def handle_no_confident_proposal(state: RecoveryState) -> dict[str, Any]:
    rejection_reason = (
        f"attempt {state['attempt_number']}: no confident proposal from the recovery engine"
    )
    return {
        "validation_result": "invalid",
        "rejection_history": [*state["rejection_history"], rejection_reason],
        "attempt_number": state["attempt_number"] + 1,
    }
