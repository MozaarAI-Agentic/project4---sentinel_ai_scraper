from recovery_engine.application.nodes.capture_screenshot import capture_screenshot
from recovery_engine.application.recovery_state import RecoveryState


class _FakeWorkerService:
    def __init__(self, screenshot_base64: str) -> None:
        self._screenshot_base64 = screenshot_base64
        self.last_call_url: str | None = None

    async def capture_screenshot(self, url: str) -> str:
        self.last_call_url = url
        return self._screenshot_base64


def _base_state(**overrides: object) -> RecoveryState:
    state: RecoveryState = {
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
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


class TestCaptureScreenshotNode:
    async def test_populates_screenshot_base64_from_the_worker_service(self) -> None:
        worker_service = _FakeWorkerService(screenshot_base64="aGVsbG8=")
        state = _base_state()

        updates = await capture_screenshot(state, worker_service=worker_service)

        assert updates["screenshot_base64"] == "aGVsbG8="

    async def test_requests_the_screenshot_for_the_job_url(self) -> None:
        worker_service = _FakeWorkerService(screenshot_base64="x")
        state = _base_state(url="https://books.example/42")

        await capture_screenshot(state, worker_service=worker_service)

        assert worker_service.last_call_url == "https://books.example/42"
