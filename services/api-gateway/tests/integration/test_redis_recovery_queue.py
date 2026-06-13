"""Tests d'intégration de RedisRecoveryQueue.

Migré de LPUSH/BRPOP (liste simple) vers XADD (Redis Stream) - voir
ADR-0014. Une liste simple retire le message avant traitement, causant une
perte de job si le consommateur crashe en cours de route (limite
documentée dès l'ADR-0004). Un Stream conserve le message dans une Pending
Entries List jusqu'à un accusé de réception explicite (XACK) - c'est le
Recovery Engine (consommateur) qui gère ce cycle, pas ce producteur.
"""

import pytest
import redis.asyncio as redis
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from api_gateway.infrastructure.redis.redis_recovery_queue import RedisRecoveryQueue
from sentinel_shared.observability.tracing import setup_tracing

_TEST_STREAM_KEY = "recovery_stream:test"


@pytest.fixture
async def redis_client() -> redis.Redis:
    client = redis.Redis(host="localhost", port=6379, db=15, decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


class TestRedisRecoveryQueueEnqueue:
    async def test_enqueues_a_job_id_into_the_stream(self, redis_client: redis.Redis) -> None:
        queue = RedisRecoveryQueue(client=redis_client, stream_key=_TEST_STREAM_KEY)

        await queue.enqueue(job_id="job-123")

        stream_length = await redis_client.xlen(_TEST_STREAM_KEY)
        assert stream_length == 1

    async def test_the_stream_entry_contains_the_job_id_field(
        self, redis_client: redis.Redis
    ) -> None:
        queue = RedisRecoveryQueue(client=redis_client, stream_key=_TEST_STREAM_KEY)

        await queue.enqueue(job_id="job-123")

        entries = await redis_client.xrange(_TEST_STREAM_KEY)
        _, fields = entries[0]
        assert fields["job_id"] == "job-123"

    async def test_enqueues_multiple_jobs_preserving_order(self, redis_client: redis.Redis) -> None:
        queue = RedisRecoveryQueue(client=redis_client, stream_key=_TEST_STREAM_KEY)

        await queue.enqueue(job_id="job-1")
        await queue.enqueue(job_id="job-2")

        entries = await redis_client.xrange(_TEST_STREAM_KEY)
        assert [fields["job_id"] for _, fields in entries] == ["job-1", "job-2"]


class TestRedisRecoveryQueueTracePropagation:
    """Le contexte de trace doit voyager DANS le message - une simple
    propagation via header HTTP ne suffit pas puisqu'il n'y a pas de
    requête HTTP entre l'enqueue et la consommation (Cycle 17)."""

    async def test_injects_the_active_trace_context_into_the_stream_entry(
        self, redis_client: redis.Redis
    ) -> None:
        tracer = setup_tracing(service_name="test-gateway", exporter=InMemorySpanExporter())
        queue = RedisRecoveryQueue(client=redis_client, stream_key=_TEST_STREAM_KEY)

        with tracer.start_as_current_span("test-request"):
            await queue.enqueue(job_id="job-with-trace")

        entries = await redis_client.xrange(_TEST_STREAM_KEY)
        _, fields = entries[0]
        assert "traceparent" in fields
