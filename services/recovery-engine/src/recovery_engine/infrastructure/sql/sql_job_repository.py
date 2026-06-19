"""Repository de lecture/mise à jour du Job, côté Recovery Engine.

Pointe vers la même table `jobs` que l'API Gateway (ADR-0006, base
partagée), mais le Recovery Engine n'en possède PAS les migrations - c'est
l'API Gateway qui reste responsable du schéma. Ce module ne fait que lire
et mettre à jour des lignes existantes, jamais créer la table lui-même en
dehors des tests (où elle est créée par la fixture, pas par ce module).
"""

from sqlalchemy import Index, JSON, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sentinel_shared.domain.job import Job
from sentinel_shared.enums import FailureReason, JobStatus


class Base(DeclarativeBase):
    pass


class JobModel(Base):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_domain_status", "domain", "status"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    required_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)


class SqlJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, job_id: str) -> Job | None:
        result = await self._session.execute(select(JobModel).where(JobModel.id == job_id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return Job(
            id=model.id,
            url=model.url,
            domain=model.domain,
            required_fields=model.required_fields,
            status=JobStatus(model.status),
            result=model.result,
            failure_reason=FailureReason(model.failure_reason) if model.failure_reason else None,
        )

    async def update(self, job: Job) -> None:
        model = await self._session.get(JobModel, job.id)
        if model is None:
            raise ValueError(f"Cannot update unknown job {job.id}")

        model.status = job.status.value
        model.result = job.result
        model.failure_reason = job.failure_reason.value if job.failure_reason else None
        await self._session.commit()
