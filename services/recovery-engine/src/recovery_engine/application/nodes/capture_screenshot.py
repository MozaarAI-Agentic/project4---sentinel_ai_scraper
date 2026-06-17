"""Nœud LangGraph : demande une capture d'écran au Worker via WorkerServicePort.

Le Recovery Engine ne possède jamais Playwright lui-même - voir
WorkerServicePort et la décision d'architecture qui l'a motivée.
"""

from recovery_engine.application.recovery_state import RecoveryState
from recovery_engine.domain.ports.worker_service_port import WorkerServicePort


async def capture_screenshot(
    state: RecoveryState, worker_service: WorkerServicePort
) -> dict[str, str]:
    screenshot_base64 = await worker_service.capture_screenshot(url=state["url"])
    return {"screenshot_base64": screenshot_base64}
