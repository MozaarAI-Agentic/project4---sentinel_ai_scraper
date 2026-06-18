"""Test d'intégration du graphe LangGraph complet.

Contrairement aux tests de nœuds isolés (Cycles 12-15), ceci exécute le
graphe COMPILÉ - le seul test qui valide réellement le câblage (routage,
noms de nœuds). C'est ce test qui a révélé le bug de routage manquant
après analyze_and_propose (voir handle_no_confident_proposal).
"""

from recovery_engine.application.dtos.worker_extraction_result import WorkerExtractionResult
from recovery_engine.application.recovery_graph import build_recovery_graph
from recovery_engine.application.recovery_state import RecoveryState
from recovery_engine.infrastructure.mock_recovery_engine import MockRecoveryEngine
from sentinel_shared.enums import FailureReason


class _FakeWorkerService:
    """Simule le Worker : validate_selectors échoue jusqu'à la version 'v3'
    d'un sélecteur, ce qui force le graphe à boucler avant de réussir."""

    def __init__(self) -> None:
        self.saved_selectors: list[tuple[str, str, str]] = []
        self._call_count = 0

    async def capture_screenshot(self, url: str) -> str:
        return "aGVsbG8="

    async def validate_selectors(self, url, domain, required_fields, selectors):  # type: ignore[no-untyped-def]
        self._call_count += 1
        if self._call_count < 2:
            return WorkerExtractionResult(
                success=False, failure_reason=FailureReason.EMPTY_REQUIRED_FIELD
            )
        return WorkerExtractionResult(success=True, data={"title": "Clean Code"})

    async def save_approved_selector(self, domain: str, field_name: str, selector_value: str) -> None:
        self.saved_selectors.append((domain, field_name, selector_value))


def _initial_state() -> RecoveryState:
    return {
        "job_id": "job-1",
        "url": "https://books.example/1",
        "domain": "books.example",
        "expected_schema": {"title": str},
        "screenshot_base64": None,
        "attempt_number": 1,
        "max_attempts": 3,
        "proposed_selectors": None,
        "recovered_data": None,
        "rejection_history": [],
        "validation_result": "pending",
        "final_status": None,
    }


class TestRecoveryGraphSuccessAfterRetry:
    async def test_graph_persists_a_selector_after_one_rejected_attempt(self) -> None:
        # seed=7, success_rate=1.0 : toujours confiant, seule la validation
        # live échoue une fois (simulée par _FakeWorkerService)
        recovery_engine = MockRecoveryEngine(seed=7, success_rate=1.0)
        worker_service = _FakeWorkerService()
        graph = build_recovery_graph(recovery_engine=recovery_engine, worker_service=worker_service)

        final_state = await graph.ainvoke(_initial_state())

        assert final_state["final_status"] == "success"
        assert len(worker_service.saved_selectors) == 1
        assert len(final_state["rejection_history"]) == 1  # 1 rejet avant le succès


class TestRecoveryGraphEscalatesAfterMaxAttempts:
    async def test_graph_escalates_when_the_engine_never_proposes_a_confident_selector(self) -> None:
        recovery_engine = MockRecoveryEngine(seed=7, success_rate=0.0)  # jamais confiant
        worker_service = _FakeWorkerService()
        graph = build_recovery_graph(recovery_engine=recovery_engine, worker_service=worker_service)

        final_state = await graph.ainvoke(_initial_state())

        assert final_state["final_status"] == "needs_human_review"
        assert worker_service.saved_selectors == []
        assert final_state["attempt_number"] == final_state["max_attempts"] + 1
