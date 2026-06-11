from api_gateway.domain.job import Job


class InMemoryJobRepository:
    """Double de test pour JobRepositoryPort. L'adaptateur PostgreSQL réel
    arrive dans un cycle ultérieur (voir ADR-0006 sur la base partagée)."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    async def save(self, job: Job) -> None:
        self._jobs[job.id] = job

    async def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)
