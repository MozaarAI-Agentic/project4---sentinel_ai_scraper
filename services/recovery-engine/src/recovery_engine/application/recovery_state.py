"""State partagé du graphe LangGraph du Recovery Engine.

TypedDict est la convention LangGraph pour représenter un state - chaque
nœud reçoit ce dict et retourne un dict partiel de mises à jour, que
LangGraph fusionne automatiquement dans le state global.

`rejection_history` est central au design (Phase 7) : sans lui, le graphe
pourrait boucler indéfiniment sur la même proposition rejetée.
"""

from typing import Literal, TypedDict


class RecoveryState(TypedDict):
    job_id: str
    url: str
    domain: str
    expected_schema: dict[str, type]
    screenshot_base64: str | None
    attempt_number: int
    max_attempts: int
    proposed_selectors: dict[str, str] | None
    recovered_data: dict[str, str] | None
    rejection_history: list[str]
    validation_result: Literal["valid", "invalid", "pending"]
    final_status: Literal["success", "needs_human_review", None]
