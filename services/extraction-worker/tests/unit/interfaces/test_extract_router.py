"""Tests du routeur POST /internal/extract.

Le contrat de réponse JSON ici DOIT correspondre exactement à ce que
HttpExtractionService (API Gateway, Cycle 6) sait interpréter - même si les
deux services sont testés indépendamment, avec leurs propres doubles. C'est
un rappel volontaire dans les commentaires de test : aucun test automatisé
ne confronte réellement les deux schémas l'un à l'autre (ce serait le rôle
d'un test de contrat inter-services, identifié comme amélioration en
Phase 9 - Testing).
"""

import httpx

from extraction_worker.domain.selector import Selector
from extraction_worker.infrastructure.fake_browser import FakeBrowser
from extraction_worker.infrastructure.in_memory_selector_repository import (
    InMemorySelectorRepository,
)
from extraction_worker.interfaces.http.app import create_app
from extraction_worker.interfaces.http.dependencies import get_browser, get_selector_repository


def _build_test_client(browser: FakeBrowser, repository: InMemorySelectorRepository) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_browser] = lambda: browser
    app.dependency_overrides[get_selector_repository] = lambda: repository
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


class TestInternalExtractSuccess:
    async def test_returns_success_payload_matching_the_api_gateway_contract(self) -> None:
        repository = InMemorySelectorRepository()
        await repository.save_selector(
            _selector("books.example", "title", "h1.title")
        )
        browser = FakeBrowser(canned_response={"title": "Clean Code"})
        client = _build_test_client(browser, repository)

        response = await client.post(
            "/internal/extract",
            json={"url": "https://books.example/1", "domain": "books.example", "required_fields": ["title"]},
        )

        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "data": {"title": "Clean Code"},
            "failure_reason": None,
        }


class TestInternalExtractFailure:
    async def test_returns_failure_payload_with_reason_when_field_is_missing(self) -> None:
        repository = InMemorySelectorRepository()  # aucun sélecteur enregistré pour "price"
        browser = FakeBrowser(canned_response={})
        client = _build_test_client(browser, repository)

        response = await client.post(
            "/internal/extract",
            json={"url": "https://books.example/1", "domain": "books.example", "required_fields": ["price"]},
        )

        assert response.status_code == 200  # échec métier, pas une erreur HTTP
        body = response.json()
        assert body["success"] is False
        assert body["failure_reason"] == "missing_required_field"


class TestInternalExtractRequestValidation:
    async def test_returns_422_when_required_fields_is_missing(self) -> None:
        client = _build_test_client(FakeBrowser(canned_response={}), InMemorySelectorRepository())

        response = await client.post(
            "/internal/extract", json={"url": "https://books.example/1", "domain": "books.example"}
        )

        assert response.status_code == 422


def _selector(domain: str, field_name: str, selector_value: str) -> Selector:
    return Selector(domain=domain, field_name=field_name, selector_value=selector_value, source="manual")
