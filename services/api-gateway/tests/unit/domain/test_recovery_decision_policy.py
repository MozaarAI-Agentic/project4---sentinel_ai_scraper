"""Tests de RecoveryDecisionPolicy.

Règle métier centrale de l'API Gateway : toutes les raisons d'échec ne
justifient pas une escalade vers Claude Computer Use. Un sélecteur cassé
est réparable par l'IA ; un site injoignable ne l'est pas. Déclencher une
recovery dans ce second cas serait un coût sans bénéfice possible, contraire
au principe deterministic-first du projet.
"""

from api_gateway.domain.policies.recovery_decision_policy import RecoveryDecisionPolicy
from sentinel_shared.enums import FailureReason


class TestNoRecoveryWhenExtractionSucceeded:
    def test_returns_false_when_there_is_no_failure_reason(self) -> None:
        assert RecoveryDecisionPolicy.should_trigger_recovery(failure_reason=None) is False


class TestRecoveryTriggeredForSelectorRelatedFailures:
    def test_returns_true_for_missing_required_field(self) -> None:
        result = RecoveryDecisionPolicy.should_trigger_recovery(
            failure_reason=FailureReason.MISSING_REQUIRED_FIELD
        )
        assert result is True

    def test_returns_true_for_empty_required_field(self) -> None:
        result = RecoveryDecisionPolicy.should_trigger_recovery(
            failure_reason=FailureReason.EMPTY_REQUIRED_FIELD
        )
        assert result is True


class TestNoRecoveryForInfrastructureFailures:
    """Aucune IA ne peut réparer un site injoignable - la recovery serait
    un coût pur sans bénéfice possible, contraire au principe
    deterministic-first du projet."""

    def test_returns_false_for_navigation_error(self) -> None:
        result = RecoveryDecisionPolicy.should_trigger_recovery(
            failure_reason=FailureReason.NAVIGATION_ERROR
        )
        assert result is False

    def test_returns_false_for_http_error(self) -> None:
        result = RecoveryDecisionPolicy.should_trigger_recovery(
            failure_reason=FailureReason.HTTP_ERROR
        )
        assert result is False
