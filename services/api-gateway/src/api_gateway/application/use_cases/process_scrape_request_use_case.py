"""Use case central de l'API Gateway.

Concrétise ADR-0003 (exécution hybride sync/async) : appelle l'Extraction
Worker, applique RecoveryDecisionPolicy sur un échec, et retourne un Job
dont le statut indique sans ambiguïté à l'appelant (à terme, la couche HTTP)
la marche à suivre - réponse immédiate, attente d'une recovery, ou échec
définitif. Aucune dépendance à un vrai client HTTP, Redis ou PostgreSQL :
tout transite par des ports.
"""

from api_gateway.application.dtos.extraction_result_dto import ExtractionResultDTO
from api_gateway.domain.job import Job
from api_gateway.domain.policies.recovery_decision_policy import RecoveryDecisionPolicy
from api_gateway.domain.ports.extraction_service_port import ExtractionServicePort
from api_gateway.domain.ports.job_repository_port import JobRepositoryPort
from api_gateway.domain.ports.recovery_queue_port import RecoveryQueuePort
from sentinel_shared.enums import JobStatus
from sentinel_shared.observability.metrics import JOB_STATUS_TOTAL


class ProcessScrapeRequestUseCase:
    def __init__(
        self,
        extraction_service: ExtractionServicePort,
        job_repository: JobRepositoryPort,
        recovery_queue: RecoveryQueuePort,
    ) -> None:
        self._extraction_service = extraction_service
        self._job_repository = job_repository
        self._recovery_queue = recovery_queue

    async def execute(self, url: str, domain: str, required_fields: list[str]) -> Job:
        job = Job.create(url=url, domain=domain, required_fields=required_fields)
        await self._job_repository.save(job)

        extraction_result = await self._extraction_service.extract(
            url=url, domain=domain, required_fields=required_fields
        )

        job = self._apply_extraction_result(job, extraction_result)
        await self._job_repository.save(job)
        JOB_STATUS_TOTAL.labels(status=job.status.value).inc()

        if job.status == JobStatus.RECOVERY_PENDING:
            await self._recovery_queue.enqueue(job.id)

        return job

    @staticmethod
    def _apply_extraction_result(job: Job, result: ExtractionResultDTO) -> Job:
        if result.success:
            return job.mark_succeeded(result=result.data)

        if RecoveryDecisionPolicy.should_trigger_recovery(result.failure_reason):
            return job.mark_recovery_pending()

        assert result.failure_reason is not None  # garanti par la policy ci-dessus
        return job.mark_failed(failure_reason=result.failure_reason)
