"""DTO de la couche applicative.

Combine le verdict de `ExtractionValidator` (domaine) avec les données
brutes extraites, pour que l'appelant du use case (API, ou plus tard le
Recovery Engine) ait accès aux deux sans avoir à les recalculer.
"""

from dataclasses import dataclass

from extraction_worker.domain.value_objects import ExtractionOutcome


@dataclass(frozen=True)
class ExtractionAttemptResult:
    outcome: ExtractionOutcome
    extracted_data: dict[str, str]
