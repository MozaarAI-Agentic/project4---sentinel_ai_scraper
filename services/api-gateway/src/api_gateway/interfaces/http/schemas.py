"""Schémas Pydantic v2 pour la frontière HTTP.

C'est précisément la frontière où Pydantic est à sa place (voir la
distinction faite au Cycle 1 : le domaine reste pur, la validation aux
frontières utilise Pydantic). Ces schémas ne fuient jamais au-delà de
`interfaces/` - le use case ne connaît que `Job` (domaine).
"""

from pydantic import BaseModel, Field

from api_gateway.domain.job import Job
from sentinel_shared.enums import JobStatus


class CreateScrapeRequestBody(BaseModel):
    url: str = Field(..., description="URL de la page à scraper")
    domain: str = Field(..., description="Domaine cible, utilisé pour résoudre les sélecteurs connus")
    required_fields: list[str] = Field(..., min_length=1, description="Champs obligatoires attendus")


class ScrapeResponseBody(BaseModel):
    job_id: str
    status: JobStatus
    result: dict[str, str] | None = None
    recovery_used: bool
    poll_url: str | None = None

    @staticmethod
    def from_job(job: Job) -> "ScrapeResponseBody":
        is_recovery_pending = job.status == JobStatus.RECOVERY_PENDING
        return ScrapeResponseBody(
            job_id=job.id,
            status=job.status,
            result=job.result,
            recovery_used=is_recovery_pending,
            poll_url=f"/api/v1/jobs/{job.id}" if is_recovery_pending else None,
        )


class ProblemDetail(BaseModel):
    """Format d'erreur RFC 7807, décidé en Phase 6 (API Design)."""

    type: str
    title: str
    status: int
    detail: str
    job_id: str
