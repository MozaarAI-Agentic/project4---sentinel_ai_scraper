"""Port abstrayant la persistance du Job.

L'implémentation de production écrit en PostgreSQL (source de vérité, voir
ADR-0006 sur la base partagée). L'implémentation en mémoire sert uniquement
aux tests.
"""

from typing import Protocol

from api_gateway.domain.job import Job


class JobRepositoryPort(Protocol):
    async def save(self, job: Job) -> None: ...

    async def get(self, job_id: str) -> Job | None: ...
