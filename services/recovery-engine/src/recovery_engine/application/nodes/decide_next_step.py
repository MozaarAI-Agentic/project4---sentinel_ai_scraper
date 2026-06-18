"""Fonction de routage pour add_conditional_edges (LangGraph).

Contrairement aux autres nœuds, ne retourne pas un dict de mises à jour -
seulement le nom du prochain nœud à exécuter. C'est pourquoi
l'incrémentation de attempt_number vit dans validate_selectors_live
(Cycle 15) et non ici : cette fonction reste une pure décision de routage,
sans effet de bord sur le state.
"""

from typing import Literal

from recovery_engine.application.recovery_state import RecoveryState

_NextNode = Literal["persist_selector", "analyze_and_propose", "escalate_human"]


def decide_next_step(state: RecoveryState) -> _NextNode:
    if state["validation_result"] == "valid":
        return "persist_selector"

    if state["attempt_number"] <= state["max_attempts"]:
        return "analyze_and_propose"

    return "escalate_human"
