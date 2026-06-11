"""Tests de ProcessScrapeRequestUseCase.

Ce use case concrétise ADR-0003 (exécution hybride sync/async) : il retourne
un Job dont le statut dit sans ambiguïté au reste du système (et à terme, à
l'API HTTP) ce qu'il doit se passer ensuite - réponse immédiate, attente
d'une recovery, ou échec définitif.

Tous les collaborateurs sont accédés via des ports, aucune dépendance
réelle à un client HTTP, Postgres ou Redis.
"""

from api_gateway.application.dtos.extraction_result_dto import ExtractionResultDTO
from api_gateway.application.use_cases.process_scrape_request_use_case import (
    ProcessScrapeRequestUseCase,
)
from api_gateway.infrastructure.fake_extraction_service import FakeExtractionService
from api_gateway.infrastructure.fake_recovery_queue import FakeRecoveryQueue
from api_gateway.infrastructure.in_memory_job_repository import InMemoryJobRepository
from sentinel_shared.enums import FailureReason, JobStatus


class TestProcessScrapeRequestSuccess:
    async def test_returns_a_success_job_with_extracted_data(self) -> None:
        extraction_service = FakeExtractionService(
            result=ExtractionResultDTO(success=True, data={"title": "Clean Code"}, failure_reason=None)
        )
        job_repository = InMemoryJobRepository()
        recovery_queue = FakeRecoveryQueue()
        use_case = ProcessScrapeRequestUseCase(
            extraction_service=extraction_service,
            job_repository=job_repository,
            recovery_queue=recovery_queue,
        )

        job = await use_case.execute(url="https://books.example/1", domain="books.example", required_fields=["title"])

        assert job.status == JobStatus.SUCCESS
        assert job.result == {"title": "Clean Code"}
        assert recovery_queue.enqueued_job_ids == []

    async def test_persists_the_successful_job(self) -> None:
        extraction_service = FakeExtractionService(
            result=ExtractionResultDTO(success=True, data={"title": "Clean Code"}, failure_reason=None)
        )
        job_repository = InMemoryJobRepository()
        use_case = ProcessScrapeRequestUseCase(
            extraction_service=extraction_service,
            job_repository=job_repository,
            recovery_queue=FakeRecoveryQueue(),
        )

        job = await use_case.execute(url="https://books.example/1", domain="books.example", required_fields=["title"])

        persisted = await job_repository.get(job.id)
        assert persisted is not None
        assert persisted.status == JobStatus.SUCCESS


class TestProcessScrapeRequestRecoverableFailure:
    async def test_enqueues_recovery_when_failure_is_selector_related(self) -> None:
        extraction_service = FakeExtractionService(
            result=ExtractionResultDTO(
                success=False, data={}, failure_reason=FailureReason.MISSING_REQUIRED_FIELD
            )
        )
        recovery_queue = FakeRecoveryQueue()
        use_case = ProcessScrapeRequestUseCase(
            extraction_service=extraction_service,
            job_repository=InMemoryJobRepository(),
            recovery_queue=recovery_queue,
        )

        job = await use_case.execute(url="https://books.example/1", domain="books.example", required_fields=["price"])

        assert job.status == JobStatus.RECOVERY_PENDING
        assert recovery_queue.enqueued_job_ids == [job.id]


class TestProcessScrapeRequestNonRecoverableFailure:
    async def test_marks_job_as_failed_without_enqueueing_recovery(self) -> None:
        extraction_service = FakeExtractionService(
            result=ExtractionResultDTO(
                success=False, data={}, failure_reason=FailureReason.NAVIGATION_ERROR
            )
        )
        recovery_queue = FakeRecoveryQueue()
        use_case = ProcessScrapeRequestUseCase(
            extraction_service=extraction_service,
            job_repository=InMemoryJobRepository(),
            recovery_queue=recovery_queue,
        )

        job = await use_case.execute(url="https://books.example/1", domain="books.example", required_fields=["price"])

        assert job.status == JobStatus.FAILED
        assert job.failure_reason == FailureReason.NAVIGATION_ERROR
        assert recovery_queue.enqueued_job_ids == []


class TestProcessScrapeRequestMetrics:
    """Vérifie l'instrumentation de job_status_total (Phase 10), via delta."""

    async def test_records_the_final_job_status(self) -> None:
        from sentinel_shared.observability.metrics import JOB_STATUS_TOTAL

        extraction_service = FakeExtractionService(
            result=ExtractionResultDTO(success=True, data={"title": "Clean Code"}, failure_reason=None)
        )
        use_case = ProcessScrapeRequestUseCase(
            extraction_service=extraction_service,
            job_repository=InMemoryJobRepository(),
            recovery_queue=FakeRecoveryQueue(),
        )

        before = JOB_STATUS_TOTAL.labels(status="success")._value.get()
        await use_case.execute(url="https://books.example/1", domain="books.example", required_fields=["title"])
        after = JOB_STATUS_TOTAL.labels(status="success")._value.get()

        assert after == before + 1
