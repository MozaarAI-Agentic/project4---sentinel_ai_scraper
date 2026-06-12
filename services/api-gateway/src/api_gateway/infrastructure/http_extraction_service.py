"""Adaptateur infrastructure : appel HTTP interne vers l'Extraction Worker.

Implémente ExtractionServicePort avec httpx.AsyncClient. Toute erreur réseau
(worker injoignable, timeout, DNS...) est capturée et transformée en un
ExtractionResultDTO avec FailureReason.HTTP_ERROR - jamais une exception qui
remonte brute jusqu'au use case. C'est cohérent avec RecoveryDecisionPolicy
(Cycle 4) : un Worker injoignable est un échec d'infrastructure, pas un
signal pour déclencher une recovery IA.
"""

import httpx

from api_gateway.application.dtos.extraction_result_dto import ExtractionResultDTO
from sentinel_shared.enums import FailureReason

_INTERNAL_EXTRACT_PATH = "/internal/extract"


class HttpExtractionService:
    def __init__(self, client: httpx.AsyncClient, base_url: str) -> None:
        self._client = client
        self._base_url = base_url

    async def extract(
        self, url: str, domain: str, required_fields: list[str]
    ) -> ExtractionResultDTO:
        try:
            response = await self._client.post(
                f"{self._base_url}{_INTERNAL_EXTRACT_PATH}",
                json={"url": url, "domain": domain, "required_fields": required_fields},
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return ExtractionResultDTO(success=False, failure_reason=FailureReason.HTTP_ERROR)

        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: httpx.Response) -> ExtractionResultDTO:
        payload = response.json()
        raw_failure_reason = payload["failure_reason"]

        try:
            failure_reason = FailureReason(raw_failure_reason) if raw_failure_reason else None
        except ValueError:
            # Contrat rompu entre services (ex: déploiement désynchronisé où le
            # Worker connaît une raison d'échec plus récente que l'API Gateway).
            # Traité comme un échec d'infrastructure, jamais comme une
            # exception non gérée qui ferait planter la requête.
            return ExtractionResultDTO(success=False, failure_reason=FailureReason.HTTP_ERROR)

        return ExtractionResultDTO(
            success=payload["success"],
            data=payload["data"],
            failure_reason=failure_reason,
        )
