"""Test d'intégration de RecoveryQueueConsumer - ferme la boucle complète
via Redis Streams (migré depuis LPUSH/BRPOP, voir ADR-0014) : lecture d'un
job_id via un consumer group, exécution du graphe de recovery, accusé de
réception explicite (XACK) uniquement après succès, mise à jour du Job.

Le test le plus important de ce fichier est celui qui simule un crash du
consommateur AVANT l'accusé de réception : contrairement à BRPOP (qui
aurait perdu le message), le Stream le garde dans une Pending Entries List,
réclamable par un autre consommateur - c'est précisément le problème que
cette migration résout (voir ADR-0004, limite documentée dès le Cycle 8).
"""

import pytest
import redis.asyncio as redis
from sqlalchemy import Index, JSON, String
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from recovery_engine.application.dtos.worker_extraction_result import WorkerExtractionResult
from recovery_engine.application.recovery_graph import build_recovery_graph
from recovery_engine.infrastructure.mock_recovery_engine import MockRecoveryEngine
from recovery_engine.infrastructure.recovery_queue_consumer import RecoveryQueueConsumer
from recovery_engine.infrastructure.sql.sql_job_repository import SqlJobRepository
from sentinel_shared.domain.job import Job
from sentinel_shared.enums import JobStatus

_TEST_REDIS_DB = 13
_STREAM_KEY = "recovery_stream:test_consumer"
_GROUP_NAME = "recovery_workers_test"


class _JobsBase(DeclarativeBase):
    pass


class _JobsTableModel(_JobsBase):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_domain_status", "domain", "status"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    required_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)


class _FakeWorkerService:
    async def capture_screenshot(self, url: str) -> str:
        return "aGVsbG8="

    async def validate_selectors(self, url, domain, required_fields, selectors):  # type: ignore[no-untyped-def]
        return WorkerExtractionResult(success=True, data={"title": "Clean Code"})

    async def save_approved_selector(self, domain: str, field_name: str, selector_value: str) -> None:
        pass


class _CrashingGraph:
    """Simule un crash du Recovery Engine en plein traitement - avant que
    process_next_job n'atteigne l'accusé de réception."""

    async def ainvoke(self, state: dict) -> dict:  # type: ignore[type-arg]
        raise RuntimeError("simulated crash mid-processing")


@pytest.fixture
async def engine() -> AsyncEngine:
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as connection:
        await connection.run_sync(_JobsBase.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncSession:
    async_session = AsyncSession(engine, expire_on_commit=False)
    yield async_session
    await async_session.close()


@pytest.fixture
async def redis_client() -> redis.Redis:
    client = redis.Redis(host="localhost", port=6379, db=_TEST_REDIS_DB, decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


async def _seed_job(session: AsyncSession, redis_client: redis.Redis) -> Job:
    job = Job.create(url="https://books.example/1", domain="books.example", required_fields=["title"])
    session.add(
        _JobsTableModel(
            id=job.id,
            url=job.url,
            domain=job.domain,
            required_fields=job.required_fields,
            status=JobStatus.RECOVERY_PENDING.value,
        )
    )
    await session.commit()
    await redis_client.xadd(_STREAM_KEY, {"job_id": job.id})
    return job


class TestRecoveryQueueConsumerClosesTheLoop:
    async def test_processes_a_job_from_the_stream_and_updates_its_status(
        self, session: AsyncSession, redis_client: redis.Redis
    ) -> None:
        job = await _seed_job(session, redis_client)
        job_repository = SqlJobRepository(session=session)
        graph = build_recovery_graph(
            recovery_engine=MockRecoveryEngine(seed=1, success_rate=1.0),
            worker_service=_FakeWorkerService(),
        )
        consumer = RecoveryQueueConsumer(
            redis_client=redis_client,
            job_repository=job_repository,
            graph=graph,
            stream_key=_STREAM_KEY,
            group_name=_GROUP_NAME,
            max_attempts=3,
        )

        processed_job_id = await consumer.process_next_job(block_ms=2000)

        assert processed_job_id == job.id
        updated_job = await job_repository.get(job.id)
        assert updated_job is not None
        assert updated_job.status == JobStatus.SUCCESS
        assert updated_job.result == {"title": "Clean Code"}

    async def test_returns_none_when_the_stream_is_empty(
        self, session: AsyncSession, redis_client: redis.Redis
    ) -> None:
        job_repository = SqlJobRepository(session=session)
        graph = build_recovery_graph(
            recovery_engine=MockRecoveryEngine(seed=1, success_rate=1.0),
            worker_service=_FakeWorkerService(),
        )
        consumer = RecoveryQueueConsumer(
            redis_client=redis_client,
            job_repository=job_repository,
            graph=graph,
            stream_key=_STREAM_KEY,
            group_name=_GROUP_NAME,
            max_attempts=3,
        )

        result = await consumer.process_next_job(block_ms=500)

        assert result is None


class TestRecoveryQueueConsumerSurvivesACrash:
    async def test_message_stays_pending_and_unacked_after_a_crash(
        self, session: AsyncSession, redis_client: redis.Redis
    ) -> None:
        """Le cœur de la migration Streams : contrairement à BRPOP, un crash
        avant XACK ne perd pas le message - il reste dans la Pending
        Entries List du groupe."""
        job = await _seed_job(session, redis_client)
        job_repository = SqlJobRepository(session=session)
        consumer = RecoveryQueueConsumer(
            redis_client=redis_client,
            job_repository=job_repository,
            graph=_CrashingGraph(),
            stream_key=_STREAM_KEY,
            group_name=_GROUP_NAME,
            max_attempts=3,
        )

        with pytest.raises(RuntimeError, match="simulated crash"):
            await consumer.process_next_job(block_ms=2000)

        pending = await redis_client.xpending(_STREAM_KEY, _GROUP_NAME)
        assert pending["pending"] == 1

        # Le job n'a jamais été mis à jour - il reste tel qu'avant le crash
        job_repository_check = SqlJobRepository(session=session)
        unchanged_job = await job_repository_check.get(job.id)
        assert unchanged_job is not None
        assert unchanged_job.status == JobStatus.RECOVERY_PENDING


class TestRecoveryQueueConsumerReclaimsStaleMessages:
    async def test_a_stale_pending_message_can_be_reclaimed_and_processed(
        self, session: AsyncSession, redis_client: redis.Redis
    ) -> None:
        """Simule une reprise après crash : un second appel à
        reclaim_stale_messages() récupère le message resté en attente et le
        traite avec succès - la garantie concrète que la migration Streams
        apporte par rapport à BRPOP."""
        job = await _seed_job(session, redis_client)
        job_repository = SqlJobRepository(session=session)

        crashing_consumer = RecoveryQueueConsumer(
            redis_client=redis_client,
            job_repository=job_repository,
            graph=_CrashingGraph(),
            stream_key=_STREAM_KEY,
            group_name=_GROUP_NAME,
            max_attempts=3,
        )
        with pytest.raises(RuntimeError):
            await crashing_consumer.process_next_job(block_ms=2000)

        healthy_graph = build_recovery_graph(
            recovery_engine=MockRecoveryEngine(seed=1, success_rate=1.0),
            worker_service=_FakeWorkerService(),
        )
        recovering_consumer = RecoveryQueueConsumer(
            redis_client=redis_client,
            job_repository=job_repository,
            graph=healthy_graph,
            stream_key=_STREAM_KEY,
            group_name=_GROUP_NAME,
            max_attempts=3,
        )

        reclaimed_job_ids = await recovering_consumer.reclaim_stale_messages(min_idle_time_ms=0)

        assert reclaimed_job_ids == [job.id]
        updated_job = await job_repository.get(job.id)
        assert updated_job is not None
        assert updated_job.status == JobStatus.SUCCESS

        pending_after = await redis_client.xpending(_STREAM_KEY, _GROUP_NAME)
        assert pending_after["pending"] == 0


class TestRecoveryQueueConsumerMetrics:
    async def test_records_the_recovery_duration(
        self, session: AsyncSession, redis_client: redis.Redis
    ) -> None:
        from sentinel_shared.observability.metrics import RECOVERY_DURATION_SECONDS

        await _seed_job(session, redis_client)
        job_repository = SqlJobRepository(session=session)
        graph = build_recovery_graph(
            recovery_engine=MockRecoveryEngine(seed=1, success_rate=1.0),
            worker_service=_FakeWorkerService(),
        )
        consumer = RecoveryQueueConsumer(
            redis_client=redis_client,
            job_repository=job_repository,
            graph=graph,
            stream_key=_STREAM_KEY,
            group_name=_GROUP_NAME,
            max_attempts=3,
        )

        before = RECOVERY_DURATION_SECONDS._sum.get()
        await consumer.process_next_job(block_ms=2000)
        after = RECOVERY_DURATION_SECONDS._sum.get()

        assert after > before


class TestRecoveryQueueConsumerTracePropagation:
    """Le test le plus important de ce fichier pour la Phase 10 : un span
    créé côté API Gateway au moment de l'enqueue doit être le PARENT du
    span créé côté Recovery Engine au moment du traitement - la preuve
    concrète que la trace survit à la traversée de la queue Redis."""

    async def test_the_consumer_span_is_a_child_of_the_producer_span(
        self, session: AsyncSession, redis_client: redis.Redis
    ) -> None:
        import opentelemetry.trace as otel_trace
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

        from sentinel_shared.observability.tracing import inject_trace_context, setup_tracing

        exporter = InMemorySpanExporter()
        tracer = setup_tracing(service_name="test-trace-propagation", exporter=exporter)

        job = await _seed_job(session, redis_client)
        # Réenfile avec un VRAI contexte de trace, en remplaçant l'entrée
        # sans trace créée par _seed_job - simule ce que RedisRecoveryQueue
        # produit réellement en production.
        await redis_client.delete(_STREAM_KEY)
        with tracer.start_as_current_span("producer-span") as producer_span:
            producer_trace_id = producer_span.get_span_context().trace_id
            trace_context = inject_trace_context()
            await redis_client.xadd(_STREAM_KEY, {"job_id": job.id, **trace_context})
        otel_trace.get_tracer_provider().force_flush()  # type: ignore[union-attr]

        job_repository = SqlJobRepository(session=session)
        graph = build_recovery_graph(
            recovery_engine=MockRecoveryEngine(seed=1, success_rate=1.0),
            worker_service=_FakeWorkerService(),
        )
        consumer = RecoveryQueueConsumer(
            redis_client=redis_client,
            job_repository=job_repository,
            graph=graph,
            stream_key=_STREAM_KEY,
            group_name=_GROUP_NAME,
            max_attempts=3,
        )

        await consumer.process_next_job(block_ms=2000)
        otel_trace.get_tracer_provider().force_flush()  # type: ignore[union-attr]

        consumer_spans = [s for s in exporter.get_finished_spans() if s.name == "recovery_engine.process_job"]
        assert len(consumer_spans) == 1
        assert consumer_spans[0].context.trace_id == producer_trace_id
