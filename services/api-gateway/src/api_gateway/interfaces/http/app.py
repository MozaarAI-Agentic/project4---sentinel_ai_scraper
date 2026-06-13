"""Point d'entrée de l'application FastAPI.

Le `lifespan` gère le cycle de vie des ressources partagées (client HTTP
réutilisé entre requêtes, factory de sessions SQLAlchemy) - créées une seule
fois au démarrage, fermées proprement à l'arrêt. C'est l'approche
recommandée par FastAPI, préférée aux anciens événements `on_event`
(dépréciés).

`create_app()` est une factory plutôt qu'une instance globale : ça permet
aux tests de créer une application fraîche par test si nécessaire, sans état
partagé accidentel entre tests.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.responses import Response
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api_gateway.infrastructure.sql.job_model import Base
from api_gateway.interfaces.http.routers.jobs_router import router as jobs_router
from sentinel_shared.observability.tracing import setup_tracing


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    database_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    extraction_worker_base_url = os.environ.get(
        "EXTRACTION_WORKER_BASE_URL", "http://extraction-worker:8000"
    )
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    app.state.db_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    app.state.extraction_worker_base_url = extraction_worker_base_url
    app.state.redis_client = redis.from_url(redis_url, decode_responses=True)

    yield

    await app.state.http_client.aclose()
    await app.state.redis_client.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    setup_tracing(service_name="api-gateway")
    HTTPXClientInstrumentor().instrument()

    app = FastAPI(
        title="SentinelAI Scraper - API Gateway",
        description="Orchestrateur du pipeline deterministic-first",
        version="0.1.0",
        lifespan=_lifespan,
    )
    FastAPIInstrumentor.instrument_app(app)
    app.include_router(jobs_router, prefix="/api/v1")

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
