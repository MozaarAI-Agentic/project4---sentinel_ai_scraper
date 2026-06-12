"""Conversion entre l'entité de domaine Job (immuable, pure) et le modèle
SQLAlchemy JobModel (mutable, lié à la base de données).

Garder cette conversion explicite dans un module dédié - plutôt que des
méthodes `to_model`/`from_model` sur les classes elles-mêmes - évite que le
domaine ait ne serait-ce qu'une connaissance passive de SQLAlchemy.
"""

from api_gateway.domain.job import Job
from api_gateway.infrastructure.sql.job_model import JobModel
from sentinel_shared.enums import FailureReason, JobStatus


def job_to_model(job: Job) -> JobModel:
    return JobModel(
        id=job.id,
        url=job.url,
        domain=job.domain,
        required_fields=job.required_fields,
        status=job.status.value,
        result=job.result,
        failure_reason=job.failure_reason.value if job.failure_reason else None,
    )


def model_to_job(model: JobModel) -> Job:
    return Job(
        id=model.id,
        url=model.url,
        domain=model.domain,
        required_fields=model.required_fields,
        status=JobStatus(model.status),
        result=model.result,
        failure_reason=FailureReason(model.failure_reason) if model.failure_reason else None,
    )
