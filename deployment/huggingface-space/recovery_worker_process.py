"""Space-specific entrypoint for the Recovery Engine's consumer process.

Mirrors recovery_engine.main's wiring exactly, but swaps the engine
selection to use DemoRecoveryEngine (this folder) instead of
MockRecoveryEngine when no ANTHROPIC_API_KEY is set - every other
building block (the graph, the consumer, the repositories, the real
Claude adapter) is imported directly from the core codebase, never
duplicated. See ADR-0017.
"""

import asyncio
import os

import httpx
import redis.asyncio as redis
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from demo_recovery_engine import DemoRecoveryEngine
from recovery_engine.application.compiled_graph_port import CompiledRecoveryGraph
from recovery_engine.application.recovery_graph import build_recovery_graph
from recovery_engine.domain.ports.recovery_engine_port import RecoveryEnginePort
from recovery_engine.infrastructure.claude_vision_recovery_engine import (
    ClaudeVisionRecoveryEngine,
)
from recovery_engine.infrastructure.http_worker_service import HttpWorkerService
from recovery_engine.infrastructure.recovery_queue_consumer import RecoveryQueueConsumer
from recovery_engine.infrastructure.sql.sql_job_repository import Base, SqlJobRepository


def _build_recovery_engine() -> RecoveryEnginePort:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return ClaudeVisionRecoveryEngine(client=AsyncAnthropic(api_key=api_key))
    return DemoRecoveryEngine()


async def _consume_forever(
    session_factory: async_sessionmaker[AsyncSession],
    redis_client: redis.Redis,
    graph: CompiledRecoveryGraph,
    max_attempts: int,
) -> None:
    while True:
        try:
            async with session_factory() as session:
                job_repository = SqlJobRepository(session=session)
                consumer = RecoveryQueueConsumer(
                    redis_client=redis_client,
                    job_repository=job_repository,
                    graph=graph,
                    max_attempts=max_attempts,
                )
                await consumer.process_next_job(block_ms=5000)
        except Exception:
            await asyncio.sleep(1)


async def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    worker_base_url = os.environ["EXTRACTION_WORKER_BASE_URL"]
    max_attempts = int(os.environ.get("RECOVERY_MAX_ATTEMPTS", "3"))

    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    redis_client = redis.from_url(redis_url, decode_responses=True)
    http_client = httpx.AsyncClient(timeout=30.0)

    worker_service = HttpWorkerService(client=http_client, base_url=worker_base_url)
    recovery_engine = _build_recovery_engine()
    graph = build_recovery_graph(recovery_engine=recovery_engine, worker_service=worker_service)

    await _consume_forever(session_factory, redis_client, graph, max_attempts)


if __name__ == "__main__":
    asyncio.run(main())
