"""L'application HTTP du Recovery Engine n'expose PAS d'API métier - ce
service consomme une queue Redis en arrière-plan (RecoveryQueueConsumer).
Cette app HTTP minimale existe uniquement pour l'observabilité (Prometheus
scrape /metrics) et les probes Kubernetes/Docker (/health), en parallèle de
la boucle de consommation (pattern sidecar)."""

import httpx

from recovery_engine.interfaces.http.app import create_app


class TestHealthEndpoint:
    async def test_returns_200(self) -> None:
        app = create_app()
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

        response = await client.get("/health")

        assert response.status_code == 200


class TestMetricsEndpoint:
    async def test_returns_prometheus_text_format(self) -> None:
        app = create_app()
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

        response = await client.get("/metrics")

        assert response.status_code == 200
        assert "recovery_attempt" in response.text
