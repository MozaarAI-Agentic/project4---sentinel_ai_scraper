"""Port abstrayant la mise en file d'un job pour recovery.

L'implémentation de production pousse dans Redis (file de tâches légère,
voir ADR-0004). Le Recovery Engine (Phase 7/8 à venir) consommera cette file
de façon asynchrone, indépendamment de la requête HTTP initiale.
"""

from typing import Protocol


class RecoveryQueuePort(Protocol):
    async def enqueue(self, job_id: str) -> None: ...
