"""Tests du nœud validate_selectors_live.

Ce nœud teste les sélecteurs proposés sur la vraie page (via WorkerServicePort,
qui réutilise l'override /internal/extract du Cycle 13). En cas d'échec, la
raison est ajoutée au rejection_history pour éviter que le prochain appel à
analyze_and_propose ne reformule la même proposition invalide - décision
posée en Phase 7.
"""

from recovery_engine.application.dtos.worker_extraction_result import WorkerExtractionResult
from recovery_engine.application.nodes.validate_selectors_live import validate_selectors_live
from recovery_engine.application.recovery_state import RecoveryState
from sentinel_shared.enums import FailureReason


class _FakeWorkerService:
    def __init__(self, result: WorkerExtractionResult) -> None:
        self._result = result
        self.last_call_selectors: dict[str, str] | None = None

    async def capture_screenshot(self, url: str) -> str:
        raise NotImplementedError("not used by this node")

    async def validate_selectors(
        self, url: str, domain: str, required_fields: list[str], selectors: dict[str, str]
    ) -> WorkerExtractionResult:
        self.last_call_selectors = selectors
        return self._result


def _base_state(**overrides: object) -> RecoveryState:
    state: RecoveryState = {
        "job_id": "job-1",
        "url": "https://books.example/1",
        "domain": "books.example",
        "expected_schema": {"title": str},
        "screenshot_base64": "aGVsbG8=",
        "attempt_number": 1,
        "max_attempts": 3,
        "proposed_selectors": {"title": "h1.title"},
        "recovered_data": None,
        "rejection_history": [],
        "validation_result": "pending",
        "final_status": None,
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


class TestValidateSelectorsLiveValid:
    async def test_sets_validation_result_to_valid_on_success(self) -> None:
        worker_service = _FakeWorkerService(
            WorkerExtractionResult(success=True, data={"title": "Clean Code"})
        )
        state = _base_state()

        updates = await validate_selectors_live(state, worker_service=worker_service)

        assert updates["validation_result"] == "valid"

    async def test_uses_the_proposed_selectors_from_the_state(self) -> None:
        worker_service = _FakeWorkerService(WorkerExtractionResult(success=True, data={}))
        state = _base_state(proposed_selectors={"title": "h1.custom-title"})

        await validate_selectors_live(state, worker_service=worker_service)

        assert worker_service.last_call_selectors == {"title": "h1.custom-title"}

    async def test_populates_recovered_data_on_success(self) -> None:
        """Nécessaire pour que la Job soit mis à jour avec les vraies
        données extraites une fois la recovery terminée (Cycle 16)."""
        worker_service = _FakeWorkerService(
            WorkerExtractionResult(success=True, data={"title": "Clean Code"})
        )
        state = _base_state()

        updates = await validate_selectors_live(state, worker_service=worker_service)

        assert updates["recovered_data"] == {"title": "Clean Code"}


class TestValidateSelectorsLiveInvalid:
    async def test_sets_validation_result_to_invalid_on_failure(self) -> None:
        worker_service = _FakeWorkerService(
            WorkerExtractionResult(success=False, failure_reason=FailureReason.EMPTY_REQUIRED_FIELD)
        )
        state = _base_state()

        updates = await validate_selectors_live(state, worker_service=worker_service)

        assert updates["validation_result"] == "invalid"

    async def test_appends_a_rejection_reason_to_the_history(self) -> None:
        worker_service = _FakeWorkerService(
            WorkerExtractionResult(success=False, failure_reason=FailureReason.EMPTY_REQUIRED_FIELD)
        )
        state = _base_state(
            proposed_selectors={"title": ".wrong-title"},
            rejection_history=["attempt 1: previous rejection"],
        )

        updates = await validate_selectors_live(state, worker_service=worker_service)

        assert updates["rejection_history"] == [
            "attempt 1: previous rejection",
            "attempt 1: selectors {'title': '.wrong-title'} rejected - reason: empty_required_field",
        ]

    async def test_resets_proposed_selectors_to_none_after_rejection(self) -> None:
        """Évite qu'une proposition rejetée ne soit accidentellement
        persistée si un nœud ultérieur lit proposed_selectors par erreur."""
        worker_service = _FakeWorkerService(
            WorkerExtractionResult(success=False, failure_reason=FailureReason.MISSING_REQUIRED_FIELD)
        )
        state = _base_state()

        updates = await validate_selectors_live(state, worker_service=worker_service)

        assert updates["proposed_selectors"] is None

    async def test_increments_attempt_number_on_rejection(self) -> None:
        """decide_next_step (Cycle 15) a besoin de ce compteur à jour pour
        décider s'il reste des tentatives avant l'escalade humaine."""
        worker_service = _FakeWorkerService(
            WorkerExtractionResult(success=False, failure_reason=FailureReason.MISSING_REQUIRED_FIELD)
        )
        state = _base_state(attempt_number=2)

        updates = await validate_selectors_live(state, worker_service=worker_service)

        assert updates["attempt_number"] == 3


class TestValidateSelectorsLiveMetrics:
    """Vérifie l'instrumentation de recovery_attempt_total (Phase 10), via delta."""

    async def test_records_a_valid_outcome(self) -> None:
        from sentinel_shared.observability.metrics import RECOVERY_ATTEMPT_TOTAL

        worker_service = _FakeWorkerService(WorkerExtractionResult(success=True, data={}))
        state = _base_state()

        before = RECOVERY_ATTEMPT_TOTAL.labels(outcome="valid")._value.get()
        await validate_selectors_live(state, worker_service=worker_service)
        after = RECOVERY_ATTEMPT_TOTAL.labels(outcome="valid")._value.get()

        assert after == before + 1

    async def test_records_an_invalid_outcome(self) -> None:
        from sentinel_shared.observability.metrics import RECOVERY_ATTEMPT_TOTAL

        worker_service = _FakeWorkerService(
            WorkerExtractionResult(success=False, failure_reason=FailureReason.EMPTY_REQUIRED_FIELD)
        )
        state = _base_state()

        before = RECOVERY_ATTEMPT_TOTAL.labels(outcome="invalid")._value.get()
        await validate_selectors_live(state, worker_service=worker_service)
        after = RECOVERY_ATTEMPT_TOTAL.labels(outcome="invalid")._value.get()

        assert after == before + 1

    async def test_does_not_increment_attempt_number_on_success(self) -> None:
        worker_service = _FakeWorkerService(WorkerExtractionResult(success=True, data={}))
        state = _base_state(attempt_number=2)

        updates = await validate_selectors_live(state, worker_service=worker_service)

        assert "attempt_number" not in updates
