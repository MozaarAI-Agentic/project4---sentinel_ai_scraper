"""Statuts du cycle de vie d'un Job, partagés entre API Gateway et Recovery
Engine. Correspond exactement à l'enum PostgreSQL défini en Phase 5
(Database Design) - le contrat de code doit rester synchronisé avec le
contrat de base de données.
"""

from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RECOVERY_PENDING = "recovery_pending"
    RECOVERING = "recovering"
    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
