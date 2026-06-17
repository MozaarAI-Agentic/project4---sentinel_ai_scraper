"""Adaptateur infrastructure : appel HTTP réel vers l'Extraction Worker
depuis le Recovery Engine. Même philosophie de gestion d'erreur que
HttpExtractionService (Cycle 6).
"""

import httpx

from recovery_engine.application.dtos.worker_extraction_result import WorkerExtractionResult
from sentinel_shared.enums import FailureReason

_SCREENSHOT_PATH = "/internal/screenshot"
_EXTRACT_PATH = "/internal/extract"
_SELECTORS_PATH = "/internal/selectors"


class HttpWorkerService:
    def __init__(self, client: httpx.AsyncClient, base_url: str) -> None:
        self._client = client
        self._base_url = base_url

    async def capture_screenshot(self, url: str) -> str:
        response = await self._client.post(f"{self._base_url}{_SCREENSHOT_PATH}", json={"url": url})
        response.raise_for_status()
        payload: dict[str, str] = response.json()
        return payload["screenshot_base64"]

    async def validate_selectors(
        self, url: str, domain: str, required_fields: list[str], selectors: dict[str, str]
    ) -> WorkerExtractionResult:
        response = await self._client.post(
            f"{self._base_url}{_EXTRACT_PATH}",
            json={
                "url": url,
                "domain": domain,
                "required_fields": required_fields,
                "selectors": selectors,
            },
        )
        response.raise_for_status()
        payload = response.json()

        raw_failure_reason = payload["failure_reason"]
        try:
            failure_reason = FailureReason(raw_failure_reason) if raw_failure_reason else None
        except ValueError:
            # Contrat rompu entre services - voir le même raisonnement au Cycle 6.
            return WorkerExtractionResult(success=False, failure_reason=FailureReason.HTTP_ERROR)

        return WorkerExtractionResult(
            success=payload["success"], data=payload["data"], failure_reason=failure_reason
        )

    async def save_approved_selector(
        self, domain: str, field_name: str, selector_value: str
    ) -> None:
        response = await self._client.post(
            f"{self._base_url}{_SELECTORS_PATH}",
            json={
                "domain": domain,
                "field_name": field_name,
                "selector_value": selector_value,
                "source": "ai_generated",
            },
        )
        response.raise_for_status()
