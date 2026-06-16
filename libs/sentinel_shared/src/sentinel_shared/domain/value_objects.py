"""Value objects de domaine partagés entre extraction-worker et recovery-engine.

`ExtractionOutcome` et `ExtractionValidator` (module voisin) encodent une
règle métier utilisée par les DEUX services : l'Extraction Worker l'applique
sur le chemin nominal, le Recovery Engine l'applique de nouveau après une
tentative de réparation IA (nœud `validate_data_schema`, Cycle 13). C'est un
véritable contrat de domaine partagé, pas une coïncidence de nommage -
migré ici en suivant le même raisonnement qu'au Cycle 4 pour FailureReason.
"""

from dataclasses import dataclass, field

from sentinel_shared.enums import FailureReason

__all__ = ["ExtractionOutcome", "FailureReason"]


@dataclass(frozen=True)
class ExtractionOutcome:
    is_success: bool
    failure_reason: FailureReason | None
    missing_fields: list[str] = field(default_factory=list)
