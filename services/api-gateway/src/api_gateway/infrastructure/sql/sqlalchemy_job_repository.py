"""Implémentation de production de JobRepositoryPort.

`save` utilise un upsert manuel (lecture puis insertion ou mise à jour des
champs) plutôt qu'un `session.merge()` : c'est plus explicite sur ce qui est
réellement mis à jour, et évite une subtilité classique de `merge()` qui
peut silencieusement écraser des champs non intentionnellement modifiés.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_gateway.domain.job import Job
from api_gateway.infrastructure.sql.job_mapper import job_to_model, model_to_job
from api_gateway.infrastructure.sql.job_model import JobModel


class SqlAlchemyJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, job: Job) -> None:
        existing = await self._session.get(JobModel, job.id)

        if existing is None:
            self._session.add(job_to_model(job))
        else:
            existing.status = job.status.value
            existing.result = job.result
            existing.failure_reason = job.failure_reason.value if job.failure_reason else None

        await self._session.commit()

    async def get(self, job_id: str) -> Job | None:
        result = await self._session.execute(select(JobModel).where(JobModel.id == job_id))
        model = result.scalar_one_or_none()
        return model_to_job(model) if model is not None else None
