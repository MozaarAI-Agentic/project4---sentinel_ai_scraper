"""Tests du routeur FastAPI /api/v1/jobs.

Utilise httpx.ASGITransport pour parler directement à l'application FastAPI
en mémoire - aucun serveur réel n'écoute sur un port. Le use case réel est
appelé (pas un double), mais avec des dépendances injectées via
`app.dependency_overrides` pointant vers des doubles de test : on valide le
contrat HTTP (codes de statut, forme JSON), pas l'orchestration métier
(déjà couverte au Cycle 5).
"""

import httpx

from api_gateway.application.dtos.extraction_result_dto import ExtractionResultDTO
from api_gateway.infrastructure.fake_extraction_service import FakeExtractionService
from api_gateway.infrastructure.fake_recovery_queue import FakeRecoveryQueue
from api_gateway.infrastructure.in_memory_job_repository import InMemoryJobRepository
from api_gateway.interfaces.http.app import create_app
from api_gateway.interfaces.http.dependencies import (
    get_extraction_service,
    get_job_repository,
    get_rate_limiter,
    get_recovery_queue,
)
from sentinel_shared.enums import FailureReason, JobStatus


class _AlwaysAllowRateLimiter:
    async def is_allowed(self, identifier: str) -> bool:
        return True


def _build_test_client(extraction_result: ExtractionResultDTO) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_extraction_service] = lambda: FakeExtractionService(
        result=extraction_result
    )
    app.dependency_overrides[get_job_repository] = lambda: InMemoryJobRepository()
    app.dependency_overrides[get_recovery_queue] = lambda: FakeRecoveryQueue()
    app.dependency_overrides[get_rate_limiter] = lambda: _AlwaysAllowRateLimiter()

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


class TestPostJobsSuccess:
    async def test_returns_200_with_extracted_data_on_success(self) -> None:
        client = _build_test_client(
            ExtractionResultDTO(success=True, data={"title": "Clean Code"}, failure_reason=None)
        )

        response = await client.post(
            "/api/v1/jobs",
            json={"url": "https://books.example/1", "domain": "books.example", "required_fields": ["title"]},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == JobStatus.SUCCESS.value
        assert body["result"] == {"title": "Clean Code"}
        assert body["recovery_used"] is False


class TestPostJobsRecoveryPending:
    async def test_returns_202_with_job_id_and_poll_url_when_recovery_triggered(self) -> None:
        client = _build_test_client(
            ExtractionResultDTO(
                success=False, data={}, failure_reason=FailureReason.MISSING_REQUIRED_FIELD
            )
        )

        response = await client.post(
            "/api/v1/jobs",
            json={"url": "https://books.example/1", "domain": "books.example", "required_fields": ["price"]},
        )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == JobStatus.RECOVERY_PENDING.value
        assert body["poll_url"] == f"/api/v1/jobs/{body['job_id']}"


class TestPostJobsNonRecoverableFailure:
    async def test_returns_422_problem_detail_when_failure_is_not_recoverable(self) -> None:
        client = _build_test_client(
            ExtractionResultDTO(success=False, data={}, failure_reason=FailureReason.NAVIGATION_ERROR)
        )

        response = await client.post(
            "/api/v1/jobs",
            json={"url": "https://books.example/1", "domain": "books.example", "required_fields": ["price"]},
        )

        assert response.status_code == 422
        body = response.json()
        # Format RFC 7807, décidé en Phase 6
        assert body["type"] == "https://sentinelai.dev/errors/validation-failed"
        assert body["status"] == 422
        assert "job_id" in body


class TestPostJobsRequestValidation:
    async def test_returns_422_when_url_is_missing(self) -> None:
        client = _build_test_client(ExtractionResultDTO(success=True, data={}, failure_reason=None))

        response = await client.post("/api/v1/jobs", json={"domain": "books.example", "required_fields": []})

        assert response.status_code == 422


class TestGetJobById:
    async def test_returns_404_for_an_unknown_job_id(self) -> None:
        client = _build_test_client(ExtractionResultDTO(success=True, data={}, failure_reason=None))

        response = await client.get("/api/v1/jobs/does-not-exist")

        assert response.status_code == 404


class TestPostJobsRateLimiting:
    async def test_returns_429_when_rate_limit_is_exceeded(self) -> None:
        app = create_app()
        app.dependency_overrides[get_extraction_service] = lambda: FakeExtractionService(
            result=ExtractionResultDTO(success=True, data={}, failure_reason=None)
        )
        app.dependency_overrides[get_job_repository] = lambda: InMemoryJobRepository()
        app.dependency_overrides[get_recovery_queue] = lambda: FakeRecoveryQueue()

        class _AlwaysDenyLimiter:
            async def is_allowed(self, identifier: str) -> bool:
                return False

        app.dependency_overrides[get_rate_limiter] = lambda: _AlwaysDenyLimiter()
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

        response = await client.post(
            "/api/v1/jobs",
            json={"url": "https://books.example/1", "domain": "books.example", "required_fields": ["title"]},
        )

        assert response.status_code == 429
