"""Test de l'endpoint /metrics - expose les métriques Prometheus au format
texte attendu par un scraper Prometheus."""

import httpx

from extraction_worker.interfaces.http.app import create_app


class TestMetricsEndpoint:
    async def test_returns_prometheus_text_format(self) -> None:
        app = create_app()
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

        response = await client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert "extraction_duration_seconds" in response.text
