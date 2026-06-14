"""Tests du routeur POST /internal/selectors.

Point d'entrée par lequel le Recovery Engine fait persister un sélecteur
approuvé - jamais en écrivant directement dans Redis/PostgreSQL depuis
recovery-engine (romprait la frontière de microservice posée au Cycle 10).
"""

import httpx

from extraction_worker.infrastructure.fake_browser import FakeBrowser
from extraction_worker.infrastructure.in_memory_selector_repository import (
    InMemorySelectorRepository,
)
from extraction_worker.interfaces.http.app import create_app
from extraction_worker.interfaces.http.dependencies import get_browser, get_selector_repository


class TestSaveSelectorEndpoint:
    async def test_saves_the_selector_and_returns_201(self) -> None:
        repository = InMemorySelectorRepository()
        app = create_app()
        app.dependency_overrides[get_browser] = lambda: FakeBrowser(canned_response={})
        app.dependency_overrides[get_selector_repository] = lambda: repository
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

        response = await client.post(
            "/internal/selectors",
            json={
                "domain": "books.example",
                "field_name": "title",
                "selector_value": "h1.title",
                "source": "ai_generated",
            },
        )

        assert response.status_code == 201
        saved = await repository.get_active_selector(domain="books.example", field_name="title")
        assert saved is not None
        assert saved.selector_value == "h1.title"
        assert saved.source == "ai_generated"
