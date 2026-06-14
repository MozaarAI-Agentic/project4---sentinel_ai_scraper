"""Point d'entrée FastAPI de l'Extraction Worker."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.responses import Response
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from extraction_worker.infrastructure.sql.selector_model import Base
from extraction_worker.interfaces.http.routers.extract_router import router as extract_router
from sentinel_shared.observability.tracing import setup_tracing


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    database_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    app.state.db_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.redis_client = redis.from_url(redis_url, decode_responses=True)

    yield

    await app.state.redis_client.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    setup_tracing(service_name="extraction-worker")

    app = FastAPI(
        title="SentinelAI Scraper - Extraction Worker",
        description="Pipeline déterministe d'extraction (Playwright + BeautifulSoup + Pydantic)",
        version="0.1.0",
        lifespan=_lifespan,
    )
    FastAPIInstrumentor.instrument_app(app)
    app.include_router(extract_router)

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
