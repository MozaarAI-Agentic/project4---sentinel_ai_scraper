"""Tests des définitions de métriques partagées.

On vérifie la structure (noms, types) plutôt que les valeurs accumulées -
les métriques Prometheus vivent dans un registre global du process, donc
leur valeur dépend de l'ordre d'exécution des tests. Les tests d'incrément
réel vivent au plus près du code instrumenté (ex: ExtractDataUseCase).
"""

from sentinel_shared.observability import metrics


class TestMetricNamesFollowPrometheusConvention:
    def test_extraction_duration_is_a_histogram_in_seconds(self) -> None:
        assert metrics.EXTRACTION_DURATION_SECONDS._name == "extraction_duration_seconds"

    def test_extraction_result_is_a_counter(self) -> None:
        assert metrics.EXTRACTION_RESULT_TOTAL._name == "extraction_result"

    def test_selector_cache_result_is_a_counter(self) -> None:
        assert metrics.SELECTOR_CACHE_RESULT_TOTAL._name == "selector_cache_result"

    def test_recovery_attempt_is_a_counter(self) -> None:
        assert metrics.RECOVERY_ATTEMPT_TOTAL._name == "recovery_attempt"

    def test_recovery_duration_is_a_histogram_in_seconds(self) -> None:
        assert metrics.RECOVERY_DURATION_SECONDS._name == "recovery_duration_seconds"

    def test_ai_recovery_cost_is_a_counter_in_usd(self) -> None:
        assert metrics.AI_RECOVERY_COST_USD_TOTAL._name == "ai_recovery_cost_usd"

    def test_job_status_is_a_counter(self) -> None:
        assert metrics.JOB_STATUS_TOTAL._name == "job_status"
