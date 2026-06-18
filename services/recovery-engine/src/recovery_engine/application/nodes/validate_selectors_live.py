"""Nœud LangGraph : teste les sélecteurs proposés sur la vraie page.

Réutilise WorkerServicePort.validate_selectors (override de /internal/extract,
Cycle 13) plutôt qu'un endpoint dédié. En cas de rejet, la raison est ajoutée
au rejection_history - décision de la Phase 7 pour éviter qu'analyze_and_propose
ne reformule la même proposition invalide au tour suivant.
"""

from typing import Any

from recovery_engine.application.recovery_state import RecoveryState
from recovery_engine.domain.ports.worker_service_port import WorkerServicePort
from sentinel_shared.observability.metrics import RECOVERY_ATTEMPT_TOTAL


async def validate_selectors_live(
    state: RecoveryState, worker_service: WorkerServicePort
) -> dict[str, Any]:
    proposed_selectors = state["proposed_selectors"]
    assert proposed_selectors is not None  # garanti par analyze_and_propose en amont

    result = await worker_service.validate_selectors(
        url=state["url"],
        domain=state["domain"],
        required_fields=list(state["expected_schema"].keys()),
        selectors=proposed_selectors,
    )

    if result.success:
        RECOVERY_ATTEMPT_TOTAL.labels(outcome="valid").inc()
        return {"validation_result": "valid", "recovered_data": result.data}

    RECOVERY_ATTEMPT_TOTAL.labels(outcome="invalid").inc()
    rejection_reason = (
        f"attempt {state['attempt_number']}: selectors {proposed_selectors} rejected - "
        f"reason: {result.failure_reason.value if result.failure_reason else 'unknown'}"
    )
    return {
        "validation_result": "invalid",
        "rejection_history": [*state["rejection_history"], rejection_reason],
        "proposed_selectors": None,
        "attempt_number": state["attempt_number"] + 1,
    }
