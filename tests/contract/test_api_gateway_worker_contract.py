"""Test de contrat : API Gateway ↔ Extraction Worker.

Contrairement aux tests unitaires (httpx.MockTransport, réponse
fabriquée à la main), ceci fait tourner la VRAIE application FastAPI du
Worker et y branche le VRAI adaptateur HttpExtractionService de l'API
Gateway - via ASGITransport, donc sans socket réseau réel, mais avec le
code de production des deux côtés. Si un des deux schémas dérive
silencieusement, ce test le détecte immédiatement.

Nécessite PYTHONPATH incluant les deux services + le shared kernel.
"""

import httpx

from api_gateway.infrastructure.http_extraction_service import HttpExtractionService
from extraction_worker.domain.selector import Selector
from extraction_worker.infrastructure.fake_browser import FakeBrowser
from extraction_worker.infrastructure.in_memory_selector_repository import (
    InMemorySelectorRepository,
)
from extraction_worker.interfaces.http.app import create_app as create_worker_app
from extraction_worker.interfaces.http.dependencies import get_browser, get_selector_repository
from sentinel_shared.enums import FailureReason


async def _build_extraction_service(
    browser: FakeBrowser, repository: InMemorySelectorRepository | None = None
) -> HttpExtractionService:
    worker_app = create_worker_app()
    worker_app.dependency_overrides[get_browser] = lambda: browser
    worker_app.dependency_overrides[get_selector_repository] = lambda: (
        repository if repository is not None else InMemorySelectorRepository()
    )

    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=worker_app), base_url="http://extraction-worker"
    )
    return HttpExtractionService(client=client, base_url="http://extraction-worker")


class TestApiGatewayWorkerContractSuccess:
    async def test_gateway_correctly_interprets_a_real_worker_success_response(self) -> None:
        # HttpExtractionService (API Gateway) ne transmet jamais de
        # sélecteurs explicites - le Worker doit en avoir un enregistré
        # pour que le chemin nominal réussisse. Oublier ceci dans le test
        # révèle exactement la valeur d'un test de contrat : il force à
        # modéliser le flux réel, pas un raccourci.
        repository = InMemorySelectorRepository()
        await repository.save_selector(
            Selector(domain="books.example", field_name="title", selector_value="h1.title", source="manual")
        )
        service = await _build_extraction_service(
            FakeBrowser(canned_response={"title": "Clean Code"}), repository=repository
        )

        result = await service.extract(
            url="https://books.example/1", domain="books.example", required_fields=["title"]
        )

        assert result.success is True
        assert result.data == {"title": "Clean Code"}
        assert result.failure_reason is None


class TestApiGatewayWorkerContractFailure:
    async def test_gateway_correctly_interprets_a_real_worker_failure_response(self) -> None:
        service = await _build_extraction_service(FakeBrowser(canned_response={}))

        result = await service.extract(
            url="https://books.example/1", domain="books.example", required_fields=["title"]
        )

        assert result.success is False
        assert result.failure_reason == FailureReason.MISSING_REQUIRED_FIELD
