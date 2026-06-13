"""Routeur HTTP pour /api/v1/jobs.

Ce module ne contient AUCUNE logique métier : il désérialise la requête,
appelle le use case, et sérialise le résultat. Toute décision (recovery ou
non, succès ou échec) a déjà été prise par ProcessScrapeRequestUseCase et
RecoveryDecisionPolicy avant que ce code ne s'exécute.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from api_gateway.application.use_cases.process_scrape_request_use_case import (
    ProcessScrapeRequestUseCase,
)
from api_gateway.domain.ports.extraction_service_port import ExtractionServicePort
from api_gateway.domain.ports.job_repository_port import JobRepositoryPort
from api_gateway.domain.ports.recovery_queue_port import RecoveryQueuePort
from api_gateway.infrastructure.redis_rate_limiter import RedisRateLimiter
from api_gateway.interfaces.http.dependencies import (
    get_extraction_service,
    get_job_repository,
    get_rate_limiter,
    get_recovery_queue,
)
from api_gateway.interfaces.http.schemas import (
    CreateScrapeRequestBody,
    ProblemDetail,
    ScrapeResponseBody,
)
from sentinel_shared.enums import JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", status_code=200)
async def create_scrape_job(
    request: Request,
    body: CreateScrapeRequestBody,
    extraction_service: ExtractionServicePort = Depends(get_extraction_service),
    job_repository: JobRepositoryPort = Depends(get_job_repository),
    recovery_queue: RecoveryQueuePort = Depends(get_recovery_queue),
    rate_limiter: RedisRateLimiter = Depends(get_rate_limiter),
) -> JSONResponse:
    client_ip = request.client.host if request.client else "unknown"
    if not await rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    use_case = ProcessScrapeRequestUseCase(
        extraction_service=extraction_service,
        job_repository=job_repository,
        recovery_queue=recovery_queue,
    )

    job = await use_case.execute(
        url=body.url, domain=body.domain, required_fields=body.required_fields
    )

    if job.status == JobStatus.SUCCESS:
        return JSONResponse(status_code=200, content=ScrapeResponseBody.from_job(job).model_dump())

    if job.status == JobStatus.RECOVERY_PENDING:
        return JSONResponse(status_code=202, content=ScrapeResponseBody.from_job(job).model_dump())

    # JobStatus.FAILED - échec non recoverable, format RFC 7807 (Phase 6)
    problem = ProblemDetail(
        type="https://sentinelai.dev/errors/validation-failed",
        title="Extraction validation failed",
        status=422,
        detail=f"Extraction failed with non-recoverable reason: {job.failure_reason}",
        job_id=job.id,
    )
    return JSONResponse(status_code=422, content=problem.model_dump())


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    job_repository: JobRepositoryPort = Depends(get_job_repository),
) -> ScrapeResponseBody:
    job = await job_repository.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return ScrapeResponseBody.from_job(job)
