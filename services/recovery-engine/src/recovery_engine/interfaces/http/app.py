"""Application HTTP minimale du Recovery Engine.

Ce service n'expose pas d'API métier - sa logique tourne dans
RecoveryQueueConsumer, une boucle de consommation Redis en arrière-plan.
Cette app existe uniquement pour l'observabilité (Prometheus) et les
probes de santé (Docker/Kubernetes) : pattern "sidecar HTTP" à côté d'un
processus principal qui n'est pas lui-même un serveur HTTP.
"""

from fastapi import FastAPI
from fastapi.responses import Response
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from sentinel_shared.observability.tracing import setup_tracing


def create_app() -> FastAPI:
    setup_tracing(service_name="recovery-engine")
    HTTPXClientInstrumentor().instrument()

    app = FastAPI(
        title="SentinelAI Scraper - Recovery Engine",
        description="Observabilité du consommateur de queue de recovery",
        version="0.1.0",
    )
    FastAPIInstrumentor.instrument_app(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
