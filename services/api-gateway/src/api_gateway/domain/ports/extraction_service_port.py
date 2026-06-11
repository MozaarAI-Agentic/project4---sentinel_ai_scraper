"""Port abstrayant l'appel à l'Extraction Worker.

L'implémentation de production fera un appel HTTP interne (voir ADR-0002 sur
les frontières de microservices). Ici, aucune trace de `httpx` ou d'URL -
seulement le contrat métier attendu.
"""

from typing import Protocol

from api_gateway.application.dtos.extraction_result_dto import ExtractionResultDTO


class ExtractionServicePort(Protocol):
    async def extract(
        self, url: str, domain: str, required_fields: list[str]
    ) -> ExtractionResultDTO: ...
