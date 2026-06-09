"""Réexport de compatibilité.

ExtractionValidator a migré vers sentinel_shared (Cycle 13) - règle de
domaine partagée avec recovery-engine (nœud validate_data_schema).
"""

from sentinel_shared.domain.extraction_validator import ExtractionValidator

__all__ = ["ExtractionValidator"]
