"""Nœud LangGraph : persiste les sélecteurs validés via le Worker.

N'écrit jamais directement dans Redis/PostgreSQL - le Recovery Engine
délègue au Worker (POST /internal/selectors) pour respecter la frontière de
microservice posée au Cycle 10.
"""

from typing import Any

from recovery_engine.application.recovery_state import RecoveryState
from recovery_engine.domain.ports.worker_service_port import WorkerServicePort


async def persist_selector(
    state: RecoveryState, worker_service: WorkerServicePort
) -> dict[str, Any]:
    proposed_selectors = state["proposed_selectors"]
    assert proposed_selectors is not None  # garanti par decide_next_step en amont

    for field_name, selector_value in proposed_selectors.items():
        await worker_service.save_approved_selector(
            domain=state["domain"], field_name=field_name, selector_value=selector_value
        )

    return {"final_status": "success"}
