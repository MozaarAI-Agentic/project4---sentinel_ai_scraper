"""Nœud LangGraph : analyse le screenshot et propose des sélecteurs.

Signature imposée par LangGraph (state -> dict de mises à jour), mais le
port `RecoveryEnginePort` est injecté explicitement plutôt que résolu
globalement - ce qui permet de tester ce nœud comme n'importe quel use case,
sans jamais instancier de graphe.
"""

from recovery_engine.application.recovery_state import RecoveryState
from recovery_engine.domain.ports.recovery_engine_port import RecoveryEnginePort


async def analyze_and_propose(
    state: RecoveryState, recovery_engine: RecoveryEnginePort
) -> dict[str, dict[str, str] | None]:
    screenshot_base64 = state["screenshot_base64"]
    if screenshot_base64 is None:
        # Invariant du graphe : ce nœud ne doit s'exécuter qu'après
        # capture_screenshot (nœud à venir), qui garantit ce champ non-None.
        # Une violation ici indique un bug d'assemblage du graphe, pas une
        # situation métier normale à gérer silencieusement.
        raise ValueError(
            "analyze_and_propose requires a screenshot_base64 already captured - "
            "this node must run after capture_screenshot in the graph."
        )

    proposal = await recovery_engine.propose_selectors(
        screenshot_base64=screenshot_base64,
        expected_schema=state["expected_schema"],
        rejection_history=state["rejection_history"],
    )

    if not proposal.is_confident:
        return {"proposed_selectors": None}

    return {"proposed_selectors": proposal.selectors}
