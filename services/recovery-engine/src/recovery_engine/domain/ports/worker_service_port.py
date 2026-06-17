"""Port abstrayant les appels du Recovery Engine vers l'Extraction Worker.

Le Recovery Engine ne possède jamais Playwright lui-même (décision prise
avant le Cycle 13) - toute action navigateur passe par ce port, implémenté
en production par des appels HTTP internes vers le Worker (même pattern que
HttpExtractionService côté API Gateway, Cycle 6).
"""

from typing import Protocol

from recovery_engine.application.dtos.worker_extraction_result import WorkerExtractionResult


class WorkerServicePort(Protocol):
    async def capture_screenshot(self, url: str) -> str:
        """Retourne une image PNG encodée en base64."""
        ...

    async def validate_selectors(
        self, url: str, domain: str, required_fields: list[str], selectors: dict[str, str]
    ) -> WorkerExtractionResult:
        """Teste des sélecteurs candidats sur la vraie page, via l'override
        de /internal/extract (Cycle 13) - sans les enregistrer au préalable."""
        ...

    async def save_approved_selector(
        self, domain: str, field_name: str, selector_value: str
    ) -> None:
        """Persiste un sélecteur approuvé - toujours source='ai_generated'
        depuis ce port, puisque seul le Recovery Engine l'appelle."""
        ...
