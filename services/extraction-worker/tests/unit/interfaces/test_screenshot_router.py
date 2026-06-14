"""Tests du routeur POST /internal/screenshot.

L'image est retournée encodée en base64 dans le JSON, jamais comme un
chemin de fichier - les deux services (Worker, Recovery Engine) sont des
conteneurs distincts sans système de fichiers partagé (voir ADR-0006, même
raisonnement que pour la base de données partagée : ici on l'évite
explicitement au lieu de le documenter comme compromis).
"""

import base64

import httpx

from extraction_worker.infrastructure.fake_browser import FakeBrowser
from extraction_worker.infrastructure.in_memory_selector_repository import (
    InMemorySelectorRepository,
)
from extraction_worker.interfaces.http.app import create_app
from extraction_worker.interfaces.http.dependencies import get_browser, get_selector_repository


class TestScreenshotEndpoint:
    async def test_returns_base64_encoded_png(self) -> None:
        app = create_app()
        app.dependency_overrides[get_browser] = lambda: FakeBrowser(
            canned_response={}, canned_screenshot=b"raw-png-bytes"
        )
        app.dependency_overrides[get_selector_repository] = lambda: InMemorySelectorRepository()
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

        response = await client.post("/internal/screenshot", json={"url": "https://books.example/1"})

        assert response.status_code == 200
        body = response.json()
        assert base64.b64decode(body["screenshot_base64"]) == b"raw-png-bytes"
