"""Schémas Pydantic pour la frontière HTTP du Worker.

Le contrat de sortie de /internal/extract (`success`, `data`,
`failure_reason`) est intentionnellement identique à celui interprété par
HttpExtractionService côté API Gateway (Cycle 6) - c'est le contrat
inter-services partagé, documenté ici et là-bas, mais jamais vérifié
automatiquement entre les deux services (limite connue, voir Phase 9 -
Testing pour un test de contrat dédié).
"""

from pydantic import BaseModel, Field

from extraction_worker.application.extraction_attempt_result import ExtractionAttemptResult


class ExtractRequestBody(BaseModel):
    url: str
    domain: str
    required_fields: list[str] = Field(..., min_length=1)
    selectors: dict[str, str] | None = Field(
        default=None,
        description="Sélecteurs candidats à tester directement, contournant le "
        "repository - utilisé par le Recovery Engine pour valider une "
        "proposition avant de l'approuver.",
    )


class ExtractResponseBody(BaseModel):
    success: bool
    data: dict[str, str]
    failure_reason: str | None

    @staticmethod
    def from_attempt_result(result: ExtractionAttemptResult) -> "ExtractResponseBody":
        return ExtractResponseBody(
            success=result.outcome.is_success,
            data=result.extracted_data,
            failure_reason=result.outcome.failure_reason.value if result.outcome.failure_reason else None,
        )


class ScreenshotRequestBody(BaseModel):
    url: str


class ScreenshotResponseBody(BaseModel):
    screenshot_base64: str


class SaveSelectorRequestBody(BaseModel):
    domain: str
    field_name: str
    selector_value: str
    source: str
