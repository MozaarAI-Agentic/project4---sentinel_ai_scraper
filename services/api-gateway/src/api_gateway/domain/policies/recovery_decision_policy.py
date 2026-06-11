"""Politique de décision : quand déclencher une recovery IA ?

C'est une règle de domaine pure de l'API Gateway - elle ne dépend d'aucune
infrastructure (pas de Redis, pas d'appel HTTP). Elle encode une distinction
métier volontaire : les échecs liés à un sélecteur (potentiellement réparés
par une regénération via Claude) justifient une recovery ; les échecs
d'infrastructure (site injoignable, erreur HTTP) ne peuvent être réparés par
aucune IA et déclencheraient un coût sans bénéfice possible.
"""

from sentinel_shared.enums import FailureReason

_RECOVERABLE_FAILURE_REASONS = frozenset(
    {
        FailureReason.MISSING_REQUIRED_FIELD,
        FailureReason.EMPTY_REQUIRED_FIELD,
    }
)


class RecoveryDecisionPolicy:
    @staticmethod
    def should_trigger_recovery(failure_reason: FailureReason | None) -> bool:
        if failure_reason is None:
            return False
        return failure_reason in _RECOVERABLE_FAILURE_REASONS
