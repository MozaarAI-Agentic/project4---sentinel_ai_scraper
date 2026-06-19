"""Consommateur de la queue de recovery Redis Streams.

Migré depuis LPUSH/BRPOP (voir ADR-0014) : un consumer group Redis Stream
garde chaque message dans une Pending Entries List (PEL) jusqu'à un accusé
de réception explicite (XACK), envoyé UNIQUEMENT après que le job ait été
traité avec succès et le Job mis à jour. Un crash avant XACK laisse le
message réclamable via `reclaim_stale_messages()` (XAUTOCLAIM) - ce qui
élimine la perte de message documentée comme limite connue depuis
l'ADR-0004.
"""

import time
from typing import Any, Protocol, cast

import redis.asyncio as redis
from opentelemetry import trace

from recovery_engine.application.compiled_graph_port import CompiledRecoveryGraph
from recovery_engine.application.recovery_state import RecoveryState
from sentinel_shared.domain.job import Job
from sentinel_shared.enums import JobStatus
from sentinel_shared.observability.metrics import RECOVERY_DURATION_SECONDS
from sentinel_shared.observability.tracing import extract_trace_context

_tracer = trace.get_tracer(__name__)


class _JobRepositoryPort(Protocol):
    async def get(self, job_id: str) -> Job | None: ...
    async def update(self, job: Job) -> None: ...


class RecoveryQueueConsumer:
    def __init__(
        self,
        redis_client: redis.Redis,
        job_repository: _JobRepositoryPort,
        graph: CompiledRecoveryGraph,
        stream_key: str = "recovery_stream",
        group_name: str = "recovery_workers",
        consumer_name: str = "consumer-1",
        max_attempts: int = 3,
    ) -> None:
        self._redis = redis_client
        self._job_repository = job_repository
        self._graph = graph
        self._stream_key = stream_key
        self._group_name = group_name
        self._consumer_name = consumer_name
        self._max_attempts = max_attempts

    async def process_next_job(self, block_ms: int = 5000) -> str | None:
        await self._ensure_group_exists()

        raw_response = await self._redis.xreadgroup(
            groupname=self._group_name,
            consumername=self._consumer_name,
            streams={self._stream_key: ">"},
            count=1,
            block=block_ms,
        )
        if not raw_response:
            return None

        # Même limite de stubs redis-py que xautoclaim ci-dessous : le type
        # de retour déclaré est partagé avec d'autres surcharges de xread*.
        # On caste vers la forme réelle documentée par Redis plutôt que de
        # laisser MyPy deviner - jamais un `type: ignore` qui masquerait le
        # raisonnement.
        response = cast(
            "list[tuple[str, list[tuple[str, dict[str, str]]]]]", raw_response
        )
        _, messages = response[0]
        message_id, fields = messages[0]

        return await self._handle_message(message_id, fields)

    async def reclaim_stale_messages(self, min_idle_time_ms: int = 30_000) -> list[str]:
        """Réclame les messages restés dans la Pending Entries List plus
        longtemps que `min_idle_time_ms` - typiquement après le crash d'un
        autre consommateur qui les avait lus sans jamais les acquitter."""
        await self._ensure_group_exists()

        raw_result = await self._redis.xautoclaim(
            name=self._stream_key,
            groupname=self._group_name,
            consumername=self._consumer_name,
            min_idle_time=min_idle_time_ms,
            start_id="0",
        )
        # Les stubs redis-py pour xautoclaim sont trop génériques pour que
        # MyPy strict les exploite directement (type de retour partagé avec
        # d'autres surcharges de la commande). On caste vers la forme
        # réelle documentée par Redis : (curseur, [(id, champs), ...], ids
        # supprimés) - jamais un simple `type: ignore` qui masquerait le
        # raisonnement.
        _next_cursor, claimed_messages, _deleted_ids = cast(
            "tuple[str, list[tuple[str, dict[str, str]]], list[str]]", raw_result
        )

        reclaimed_job_ids = []
        for message_id, fields in claimed_messages:
            job_id = await self._handle_message(message_id, fields)
            if job_id is not None:
                reclaimed_job_ids.append(job_id)
        return reclaimed_job_ids

    async def _ensure_group_exists(self) -> None:
        try:
            await self._redis.xgroup_create(
                name=self._stream_key, groupname=self._group_name, id="0", mkstream=True
            )
        except redis.ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise

    async def _handle_message(self, message_id: str, fields: dict[str, str]) -> str | None:
        job_id = fields["job_id"]
        # Le contexte de trace voyage dans les champs du message (injecté
        # par RedisRecoveryQueue.enqueue côté API Gateway) - on l'extrait
        # pour que ce span continue la MÊME trace, pas une nouvelle
        # déconnectée de la requête HTTP d'origine.
        trace_carrier = {k: v for k, v in fields.items() if k != "job_id"}
        parent_context = extract_trace_context(trace_carrier)

        with _tracer.start_as_current_span("recovery_engine.process_job", context=parent_context):
            return await self._process_job(job_id, message_id)

    async def _process_job(self, job_id: str, message_id: str) -> str | None:
        job = await self._job_repository.get(job_id)
        if job is None:
            # Job disparu ou jamais créé - situation anormale mais pas
            # fatale ; on acquitte quand même pour ne pas bloquer la PEL
            # indéfiniment sur un message qui ne sera jamais traitable.
            await self._redis.xack(self._stream_key, self._group_name, message_id)
            return None

        initial_state = self._build_initial_state(job)

        started_at = time.monotonic()
        final_state = await self._graph.ainvoke(initial_state)
        RECOVERY_DURATION_SECONDS.observe(time.monotonic() - started_at)

        await self._apply_final_state(job, final_state)
        await self._redis.xack(self._stream_key, self._group_name, message_id)

        return job_id

    def _build_initial_state(self, job: Job) -> RecoveryState:
        return {
            "job_id": job.id,
            "url": job.url,
            "domain": job.domain,
            "expected_schema": dict.fromkeys(job.required_fields, str),
            "screenshot_base64": None,
            "attempt_number": 1,
            "max_attempts": self._max_attempts,
            "proposed_selectors": None,
            "recovered_data": None,
            "rejection_history": [],
            "validation_result": "pending",
            "final_status": None,
        }

    async def _apply_final_state(self, job: Job, final_state: dict[str, Any]) -> None:
        if final_state["final_status"] == "success":
            updated_job = job.mark_succeeded(result=final_state["recovered_data"])
        else:
            updated_job = Job(
                id=job.id,
                url=job.url,
                domain=job.domain,
                required_fields=job.required_fields,
                status=JobStatus.NEEDS_HUMAN_REVIEW,
            )
        await self._job_repository.update(updated_job)
