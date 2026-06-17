"""Port abstrayant le moteur de recovery visuel.

Le graphe LangGraph (à construire) ne dépendra que de cette interface.
MockRecoveryEngine (ce cycle) et ClaudeRecoveryEngine (activé en fin de
Phase 8, décision prise en Phase 1) implémentent toutes deux ce contrat de
façon interchangeable.
"""

from typing import Protocol

from recovery_engine.domain.value_objects import SelectorProposal


class RecoveryEnginePort(Protocol):
    async def propose_selectors(
        self,
        screenshot_base64: str,
        expected_schema: dict[str, type],
        rejection_history: list[str],
    ) -> SelectorProposal: ...
