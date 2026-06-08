"""Contrats d'énumération partagés entre les microservices SentinelAI.

Ce module fait partie du shared kernel (sentinel_shared) : il ne contient
JAMAIS de logique métier, uniquement des contrats de données que plusieurs
services doivent interpréter de façon identique. Ici, `FailureReason` est
produit par l'Extraction Worker et consommé par l'API Gateway pour décider
si une recovery IA est justifiée (voir RecoveryDecisionPolicy).
"""

from enum import Enum


class FailureReason(str, Enum):
    """Catégorise pourquoi une extraction a échoué.

    Distinction volontaire en deux familles :
    - Échecs liés au sélecteur (MISSING_REQUIRED_FIELD, EMPTY_REQUIRED_FIELD) :
      potentiellement réparables par une regénération de sélecteur via IA.
    - Échecs d'infrastructure (NAVIGATION_ERROR, HTTP_ERROR) : aucune IA ne
      peut réparer un site injoignable - une recovery serait un coût pur
      sans bénéfice possible.
    """

    # Famille "sélecteur" — recoverable par IA
    MISSING_REQUIRED_FIELD = "missing_required_field"
    EMPTY_REQUIRED_FIELD = "empty_required_field"

    # Famille "infrastructure" — non recoverable par IA
    NAVIGATION_ERROR = "navigation_error"
    HTTP_ERROR = "http_error"
