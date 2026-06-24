"""Test de contrat : Recovery Engine ↔ Extraction Worker.

Fait tourner la vraie app FastAPI du Worker et y branche le vrai
HttpWorkerService du Recovery Engine, pour les 3 endpoints réellement
utilisés : /internal/screenshot, /internal/extract (override), et
/internal/selectors.
"""

import base64

import httpx

from extraction_worker.infrastructure.fake_browser import FakeBrowser
from extraction_worker.infrastructure.in_memory_selector_repository import (
    InMemorySelectorRepository,
)
from extraction_worker.interfaces.http.app import create_app as create_worker_app
from extraction_worker.interfaces.http.dependencies import get_browser, get_selector_repository
from recovery_engine.infrastructure.http_worker_service import HttpWorkerService
from sentinel_shared.enums import FailureReason


def _build_worker_service(
    browser: FakeBrowser, repository: InMemorySelectorRepository | None = None
) -> HttpWorkerService:
    worker_app = create_worker_app()
    worker_app.dependency_overrides[get_browser] = lambda: browser
    worker_app.dependency_overrides[get_selector_repository] = lambda: (
        repository if repository is not None else InMemorySelectorRepository()
    )

    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=worker_app), base_url="http://extraction-worker"
    )
    return HttpWorkerService(client=client, base_url="http://extraction-worker")


class TestRecoveryEngineWorkerContractScreenshot:
    async def test_receives_a_valid_base64_screenshot_from_the_real_worker(self) -> None:
        service = _build_worker_service(FakeBrowser(canned_response={}, canned_screenshot=b"real-bytes"))

        result = await service.capture_screenshot(url="https://books.example/1")

        assert base64.b64decode(result) == b"real-bytes"


class TestRecoveryEngineWorkerContractValidateSelectors:
    async def test_candidate_selectors_are_correctly_tested_by_the_real_worker(self) -> None:
        service = _build_worker_service(FakeBrowser(canned_response={"title": "Clean Code"}))

        result = await service.validate_selectors(
            url="https://books.example/1",
            domain="books.example",
            required_fields=["title"],
            selectors={"title": "h1.title"},
        )

        assert result.success is True
        assert result.data == {"title": "Clean Code"}

    async def test_a_rejected_candidate_returns_the_correct_failure_reason(self) -> None:
        service = _build_worker_service(FakeBrowser(canned_response={}))

        result = await service.validate_selectors(
            url="https://books.example/1",
            domain="books.example",
            required_fields=["title"],
            selectors={"title": ".wrong-selector"},
        )

        assert result.success is False
        assert result.failure_reason == FailureReason.MISSING_REQUIRED_FIELD


class TestRecoveryEngineWorkerContractSaveSelector:
    async def test_an_approved_selector_is_really_persisted_by_the_worker(self) -> None:
        repository = InMemorySelectorRepository()
        service = _build_worker_service(FakeBrowser(canned_response={}), repository=repository)

        await service.save_approved_selector(
            domain="books.example", field_name="title", selector_value="h1.title"
        )

        saved = await repository.get_active_selector(domain="books.example", field_name="title")
        assert saved is not None
        assert saved.selector_value == "h1.title"
        assert saved.source == "ai_generated"
