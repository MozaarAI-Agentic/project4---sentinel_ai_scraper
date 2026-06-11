"""Réexport de compatibilité.

Job a migré vers sentinel_shared (Cycle 16) - contrat de domaine partagé
avec recovery-engine, qui lit et met à jour ce même Job après une recovery.
"""

from sentinel_shared.domain.job import Job

__all__ = ["Job"]
