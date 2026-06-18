from recovery_engine.application.nodes.escalate_human import escalate_human
from recovery_engine.application.nodes.persist_selector import persist_selector
from recovery_engine.application.recovery_state import RecoveryState


class _FakeWorkerService:
    def __init__(self) -> None:
        self.saved_selectors: list[tuple[str, str, str]] = []

    async def capture_screenshot(self, url: str) -> str:
        raise NotImplementedError

    async def validate_selectors(self, url, domain, required_fields, selectors):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def save_approved_selector(self, domain: str, field_name: str, selector_value: str) -> None:
        self.saved_selectors.append((domain, field_name, selector_value))


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
        "validation_result": "valid",
        "final_status": None,
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


class TestPersistSelectorNode:
    async def test_saves_each_approved_field_selector(self) -> None:
        worker_service = _FakeWorkerService()
        state = _base_state(proposed_selectors={"title": "h1.title", "price": ".price"})

        updates = await persist_selector(state, worker_service=worker_service)

        assert set(worker_service.saved_selectors) == {
            ("books.example", "title", "h1.title"),
            ("books.example", "price", ".price"),
        }
        assert updates["final_status"] == "success"


class TestEscalateHumanNode:
    def test_sets_final_status_to_needs_human_review(self) -> None:
        state = _base_state(validation_result="invalid")

        updates = escalate_human(state)

        assert updates["final_status"] == "needs_human_review"
