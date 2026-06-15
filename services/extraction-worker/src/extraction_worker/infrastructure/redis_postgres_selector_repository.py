"""Implémentation de production de SelectorRepositoryPort.

Stratégie cache-aside : Redis est toujours consulté en premier ; en cas de
cache miss, PostgreSQL (source de vérité, avec versionnement complet) est
lu, et le résultat réchauffe Redis avant d'être retourné. `save_selector`
écrit dans PostgreSQL d'abord (source de vérité), puis dans Redis - un échec
d'écriture Redis ne doit jamais faire perdre l'écriture PostgreSQL, qui a
déjà réussi à ce stade.
"""

import json

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extraction_worker.domain.selector import Selector, SelectorSource
from extraction_worker.infrastructure.sql.selector_model import SelectorModel
from sentinel_shared.observability.metrics import SELECTOR_CACHE_RESULT_TOTAL


def _cache_key(domain: str, field_name: str) -> str:
    return f"selector:{domain}:{field_name}"


class RedisPostgresSelectorRepository:
    def __init__(self, session: AsyncSession, redis_client: redis.Redis) -> None:
        self._session = session
        self._redis = redis_client

    async def get_active_selector(self, domain: str, field_name: str) -> Selector | None:
        cached = await self._get_from_cache(domain, field_name)
        if cached is not None:
            SELECTOR_CACHE_RESULT_TOTAL.labels(result="hit").inc()
            return cached

        SELECTOR_CACHE_RESULT_TOTAL.labels(result="miss").inc()
        from_db = await self._get_from_postgres(domain, field_name)
        if from_db is not None:
            await self._write_to_cache(from_db)
        return from_db

    async def save_selector(self, selector: Selector) -> None:
        saved = await self._save_to_postgres(selector)
        await self._write_to_cache(saved)

    async def _get_from_cache(self, domain: str, field_name: str) -> Selector | None:
        raw = await self._redis.get(_cache_key(domain, field_name))
        if raw is None:
            return None
        payload = json.loads(raw)
        return Selector(
            domain=domain,
            field_name=field_name,
            selector_value=payload["selector_value"],
            source=payload["source"],
            version=payload["version"],
        )

    async def _write_to_cache(self, selector: Selector) -> None:
        payload = json.dumps(
            {
                "selector_value": selector.selector_value,
                "source": selector.source,
                "version": selector.version,
            }
        )
        await self._redis.set(_cache_key(selector.domain, selector.field_name), payload)

    async def _get_from_postgres(self, domain: str, field_name: str) -> Selector | None:
        result = await self._session.execute(
            select(SelectorModel).where(
                SelectorModel.domain == domain,
                SelectorModel.field_name == field_name,
                SelectorModel.is_active.is_(True),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_selector(model)

    async def _save_to_postgres(self, selector: Selector) -> Selector:
        previous_result = await self._session.execute(
            select(SelectorModel).where(
                SelectorModel.domain == selector.domain,
                SelectorModel.field_name == selector.field_name,
                SelectorModel.is_active.is_(True),
            )
        )
        previous = previous_result.scalar_one_or_none()

        next_version = 1
        if previous is not None:
            previous.is_active = False
            next_version = previous.version + 1

        new_model = SelectorModel(
            domain=selector.domain,
            field_name=selector.field_name,
            selector_value=selector.selector_value,
            version=next_version,
            source=selector.source,
            is_active=True,
        )
        self._session.add(new_model)
        await self._session.commit()

        return self._model_to_selector(new_model)

    @staticmethod
    def _model_to_selector(model: SelectorModel) -> Selector:
        source: SelectorSource = "manual" if model.source == "manual" else "ai_generated"
        return Selector(
            domain=model.domain,
            field_name=model.field_name,
            selector_value=model.selector_value,
            source=source,
            version=model.version,
        )
