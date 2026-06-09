"""Réexport de compatibilité.

ExtractionOutcome et FailureReason ont migré vers sentinel_shared (Cycle 13)
- règle de domaine partagée avec recovery-engine, pas propre à ce service.
Ce module reste en place pour que le reste du code de l'Extraction Worker
continue d'importer depuis un chemin stable, sans savoir que la définition
vit désormais dans le shared kernel.
"""

from sentinel_shared.domain.value_objects import ExtractionOutcome, FailureReason

__all__ = ["ExtractionOutcome", "FailureReason"]
