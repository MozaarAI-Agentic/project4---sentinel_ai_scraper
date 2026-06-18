"""DTO représentant le résultat d'un appel /internal/extract, vu depuis le
Recovery Engine. Propre à ce service - pas dans sentinel_shared, car c'est
un contrat de client HTTP consommé par ce seul service, pas une règle de
domaine partagée (distinction posée au Cycle 13 ; comparer avec
ExtractionResultDTO côté API Gateway, qui a la même forme mais reste un
objet distinct pour la même raison).
"""

from dataclasses import dataclass, field

from sentinel_shared.enums import FailureReason


@dataclass(frozen=True)
class WorkerExtractionResult:
    success: bool
    data: dict[str, str] = field(default_factory=dict)
    failure_reason: FailureReason | None = None
