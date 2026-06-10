"""Use case central du pipeline déterministe : extraire les données d'une
page en résolvant les sélecteurs connus, puis valider le résultat.

Ce use case ne dépend que de ports (BrowserPort, SelectorRepositoryPort) et
d'un service de domaine pur (ExtractionValidator). Il ignore totalement
Playwright, Redis ou PostgreSQL - c'est ce qui permet de le tester
entièrement avec des doubles rapides et déterministes.

Instrumenté avec les métriques Prometheus partagées (Phase 10) : la durée
et le résultat de chaque tentative d'extraction alimentent directement les
KPIs "taux de succès" et "latence d'extraction" définis en Phase 2.
"""

import time

from extraction_worker.application.extraction_attempt_result import ExtractionAttemptResult
from extraction_worker.domain.extraction_validator import ExtractionValidator
from extraction_worker.domain.ports.browser_port import BrowserPort
from extraction_worker.domain.ports.selector_repository_port import SelectorRepositoryPort
from sentinel_shared.observability.metrics import EXTRACTION_DURATION_SECONDS, EXTRACTION_RESULT_TOTAL


class ExtractDataUseCase:
    def __init__(self, browser: BrowserPort, selector_repository: SelectorRepositoryPort) -> None:
        self._browser = browser
        self._selector_repository = selector_repository

    async def execute(
        self,
        url: str,
        domain: str,
        required_fields: list[str],
        candidate_selectors: dict[str, str] | None = None,
    ) -> ExtractionAttemptResult:
        started_at = time.monotonic()

        selectors = (
            candidate_selectors
            if candidate_selectors is not None
            else await self._resolve_known_selectors(domain, required_fields)
        )
        extracted_data = await self._browser.extract_fields(url=url, selectors=selectors)

        validator = ExtractionValidator(required_fields=required_fields)
        outcome = validator.validate(extracted_data)

        outcome_label = "success" if outcome.is_success else "failure"
        EXTRACTION_DURATION_SECONDS.labels(domain=domain, outcome=outcome_label).observe(
            time.monotonic() - started_at
        )
        EXTRACTION_RESULT_TOTAL.labels(domain=domain, outcome=outcome_label).inc()

        return ExtractionAttemptResult(outcome=outcome, extracted_data=extracted_data)

    async def _resolve_known_selectors(
        self, domain: str, required_fields: list[str]
    ) -> dict[str, str]:
        """Ne retient que les champs pour lesquels un sélecteur est déjà connu.

        Un champ sans sélecteur enregistré n'est jamais transmis au navigateur :
        il ressortira naturellement comme "manquant" lors de la validation,
        avec exactement le même symptôme qu'un sélecteur cassé. Pas de cas
        spécial à gérer plus loin dans le pipeline.
        """
        resolved: dict[str, str] = {}
        for field_name in required_fields:
            selector = await self._selector_repository.get_active_selector(domain, field_name)
            if selector is not None:
                resolved[field_name] = selector.selector_value
        return resolved
