"""DTO représentant le résultat d'un appel à l'Extraction Worker.

Vu depuis l'API Gateway, l'Extraction Worker est une frontière HTTP - ce
DTO représente la réponse JSON désérialisée, indépendamment du fait qu'elle
provienne d'un vrai appel HTTP (production) ou d'un double de test.
"""

from dataclasses import dataclass, field

from sentinel_shared.enums import FailureReason


@dataclass(frozen=True)
class ExtractionResultDTO:
    success: bool
    data: dict[str, str] = field(default_factory=dict)
    failure_reason: FailureReason | None = None
