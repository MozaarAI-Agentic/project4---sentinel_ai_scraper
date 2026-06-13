"""Composition root de l'API Gateway.

C'est le SEUL endroit du service où les adaptateurs concrets (HTTP réel,
SQLAlchemy réel, Redis réel) sont assemblés. Le reste du code ne connaît
que les ports. En test, `app.dependency_overrides` remplace ces fonctions
par des doubles - voir tests/unit/interfaces/test_jobs_router.py.
"""

from collections.abc import AsyncGenerator

import httpx
from fastapi import Request

from api_gateway.domain.ports.extraction_service_port import ExtractionServicePort
from api_gateway.domain.ports.job_repository_port import JobRepositoryPort
from api_gateway.domain.ports.recovery_queue_port import RecoveryQueuePort
from api_gateway.infrastructure.http_extraction_service import HttpExtractionService
from api_gateway.infrastructure.redis.redis_recovery_queue import RedisRecoveryQueue
from api_gateway.infrastructure.redis_rate_limiter import RedisRateLimiter
from api_gateway.infrastructure.sql.sqlalchemy_job_repository import SqlAlchemyJobRepository


def get_rate_limiter(request: Request) -> RedisRateLimiter:
    return RedisRateLimiter(redis_client=request.app.state.redis_client, limit=60, window_seconds=60)


def get_extraction_service(request: Request) -> ExtractionServicePort:
    client: httpx.AsyncClient = request.app.state.http_client
    base_url: str = request.app.state.extraction_worker_base_url
    return HttpExtractionService(client=client, base_url=base_url)


async def get_job_repository(request: Request) -> AsyncGenerator[JobRepositoryPort, None]:
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        yield SqlAlchemyJobRepository(session=session)


def get_recovery_queue(request: Request) -> RecoveryQueuePort:
    return RedisRecoveryQueue(client=request.app.state.redis_client)
