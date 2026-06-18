"""Nœud LangGraph : escalade vers une revue humaine.

Fonction synchrone et pure - aucune dépendance externe pour le MVP. La
notification réelle (Slack, email, ticket) est une amélioration enterprise
documentée, pas codée maintenant (voir Phase 7 - AI Agent Design).
"""

from typing import Any

from recovery_engine.application.recovery_state import RecoveryState


def escalate_human(state: RecoveryState) -> dict[str, Any]:
    return {"final_status": "needs_human_review"}
