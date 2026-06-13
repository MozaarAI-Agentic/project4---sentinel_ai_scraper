"""Implémentation de production de RecoveryQueuePort.

Migré de LPUSH/BRPOP vers Redis Streams (XADD) - voir ADR-0014. Le
contexte OpenTelemetry actif est injecté directement dans les champs du
message : un header HTTP ne suffit pas ici, il n'y a pas de requête HTTP
entre cet enqueue et la consommation asynchrone par le Recovery Engine
(voir ADR-0015, Cycle 17).
"""

import redis.asyncio as redis

from sentinel_shared.observability.tracing import inject_trace_context


class RedisRecoveryQueue:
    def __init__(self, client: redis.Redis, stream_key: str = "recovery_stream") -> None:
        self._client = client
        self._stream_key = stream_key

    async def enqueue(self, job_id: str) -> None:
        trace_context = inject_trace_context()
        await self._client.xadd(self._stream_key, {"job_id": job_id, **trace_context})
