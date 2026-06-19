"""Point d'entrée de production du Recovery Engine.

Lance en parallèle, dans le même processus asyncio :
1. Le serveur HTTP sidecar (health/metrics, voir Phase 10)
2. La boucle de consommation de la queue de recovery (jamais construite
   avant ce cycle - RecoveryQueueConsumer n'était testé que sur un seul
   appel à process_next_job(), jamais en boucle continue)

Une session SQLAlchemy fraîche est ouverte à chaque itération de la boucle
plutôt que réutilisée sur toute la durée de vie du processus - plus simple
à raisonner, au prix d'une session par poll même quand la queue est vide.
Documenté comme optimisation possible (voir ROADMAP.md), pas un oubli.
"""

import asyncio
import os

import httpx
import redis.asyncio as redis
import uvicorn
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from recovery_engine.application.compiled_graph_port import CompiledRecoveryGraph
from recovery_engine.application.recovery_graph import build_recovery_graph
from recovery_engine.domain.ports.recovery_engine_port import RecoveryEnginePort
from recovery_engine.infrastructure.claude_vision_recovery_engine import (
    ClaudeVisionRecoveryEngine,
)
from recovery_engine.infrastructure.http_worker_service import HttpWorkerService
from recovery_engine.infrastructure.mock_recovery_engine import MockRecoveryEngine
from recovery_engine.infrastructure.recovery_queue_consumer import RecoveryQueueConsumer
from recovery_engine.infrastructure.sql.sql_job_repository import Base, SqlJobRepository
from recovery_engine.interfaces.http.app import create_app


def _build_recovery_engine() -> RecoveryEnginePort:
    """Bascule vers Claude réel dès qu'une clé API est fournie - le mock
    reste le comportement par défaut, cohérent avec la décision de la
    Phase 1 (activation consciente, jamais accidentelle)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return ClaudeVisionRecoveryEngine(client=AsyncAnthropic(api_key=api_key))

    mock_success_rate = float(os.environ.get("MOCK_RECOVERY_SUCCESS_RATE", "0.7"))
    # seed=None en production : variance réelle, pas le déterminisme des tests
    return MockRecoveryEngine(success_rate=mock_success_rate)


async def _consume_forever(
    session_factory: async_sessionmaker[AsyncSession],
    redis_client: redis.Redis,
    graph: CompiledRecoveryGraph,
    max_attempts: int,
    stream_key: str,
    group_name: str,
    consumer_name: str,
) -> None:
    while True:
        try:
            async with session_factory() as session:
                job_repository = SqlJobRepository(session=session)
                consumer = RecoveryQueueConsumer(
                    redis_client=redis_client,
                    job_repository=job_repository,
                    graph=graph,
                    stream_key=stream_key,
                    group_name=group_name,
                    consumer_name=consumer_name,
                    max_attempts=max_attempts,
                )
                await consumer.process_next_job(block_ms=5000)
        except Exception:
            # Une erreur ponctuelle (Redis temporairement indisponible, etc.)
            # ne doit jamais tuer la boucle du consommateur. Logging réel
            # avec Loguru identifié comme amélioration (voir ROADMAP.md) -
            # pour l'instant, on continue après une courte pause. Le message
            # en cours (s'il y en avait un) reste dans la Pending Entries
            # List Redis Streams - réclamable via reclaim_stale_messages(),
            # jamais perdu (voir ADR-0014).
            await asyncio.sleep(1)


async def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    worker_base_url = os.environ["EXTRACTION_WORKER_BASE_URL"]
    max_attempts = int(os.environ.get("RECOVERY_MAX_ATTEMPTS", "3"))
    stream_key = os.environ.get("RECOVERY_STREAM_KEY", "recovery_stream")
    group_name = os.environ.get("RECOVERY_GROUP_NAME", "recovery_workers")
    consumer_name = os.environ.get("RECOVERY_CONSUMER_NAME", "consumer-1")
    http_port = int(os.environ.get("PORT", "8000"))

    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    redis_client = redis.from_url(redis_url, decode_responses=True)
    http_client = httpx.AsyncClient(timeout=30.0)

    worker_service = HttpWorkerService(client=http_client, base_url=worker_base_url)
    recovery_engine = _build_recovery_engine()
    graph = build_recovery_graph(recovery_engine=recovery_engine, worker_service=worker_service)

    app = create_app()
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=http_port, log_level="info"))

    await asyncio.gather(
        server.serve(),
        _consume_forever(
            session_factory, redis_client, graph, max_attempts, stream_key, group_name, consumer_name
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
