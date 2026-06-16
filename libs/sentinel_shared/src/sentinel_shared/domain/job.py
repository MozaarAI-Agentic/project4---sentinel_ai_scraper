"""Entité Job, partagée entre API Gateway (l'écrit, Cycle 5/7) et Recovery
Engine (le lit et le met à jour après une recovery, Cycle 16). C'est un
contrat de domaine réellement partagé entre deux bounded contexts - migré
ici en suivant le même raisonnement qu'au Cycle 4 (FailureReason) et
Cycle 13 (ExtractionValidator).

Suit la même philosophie d'immuabilité que le reste du domaine : chaque
transition d'état retourne un NOUVEAU Job plutôt que de muter l'instance
existante.
"""

from dataclasses import dataclass, replace
from uuid import uuid4

from sentinel_shared.enums import FailureReason, JobStatus


@dataclass(frozen=True)
class Job:
    id: str
    url: str
    domain: str
    required_fields: list[str]
    status: JobStatus
    result: dict[str, str] | None = None
    failure_reason: FailureReason | None = None

    @staticmethod
    def create(url: str, domain: str, required_fields: list[str]) -> "Job":
        return Job(
            id=str(uuid4()),
            url=url,
            domain=domain,
            required_fields=required_fields,
            status=JobStatus.PENDING,
        )

    def mark_succeeded(self, result: dict[str, str]) -> "Job":
        return replace(self, status=JobStatus.SUCCESS, result=result)

    def mark_recovery_pending(self) -> "Job":
        return replace(self, status=JobStatus.RECOVERY_PENDING)

    def mark_failed(self, failure_reason: FailureReason) -> "Job":
        return replace(self, status=JobStatus.FAILED, failure_reason=failure_reason)
