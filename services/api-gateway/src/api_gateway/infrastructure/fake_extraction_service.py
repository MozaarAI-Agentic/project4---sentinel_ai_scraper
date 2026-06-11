from api_gateway.application.dtos.extraction_result_dto import ExtractionResultDTO


class FakeExtractionService:
    """Double de test pour ExtractionServicePort. L'adaptateur HTTP réel vers
    l'Extraction Worker arrive dans un cycle ultérieur."""

    def __init__(self, result: ExtractionResultDTO) -> None:
        self._result = result

    async def extract(
        self, url: str, domain: str, required_fields: list[str]
    ) -> ExtractionResultDTO:
        return self._result
