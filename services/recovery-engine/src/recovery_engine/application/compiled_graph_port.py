"""Type public du graphe LangGraph compilé.

`StateGraph.compile()` de LangGraph ne fournit pas de type public simple à
annoter - ce Protocol capture le seul contrat dont le reste du code a
besoin (`ainvoke`), sans dépendre des détails internes de LangGraph.
Remplace le retour `object` de `build_recovery_graph`, qui empêchait MyPy
strict de vérifier correctement son utilisation dans `main.py` et
`RecoveryQueueConsumer`.
"""

from typing import Any, Protocol

from recovery_engine.application.recovery_state import RecoveryState


class CompiledRecoveryGraph(Protocol):
    async def ainvoke(self, state: RecoveryState) -> dict[str, Any]: ...
