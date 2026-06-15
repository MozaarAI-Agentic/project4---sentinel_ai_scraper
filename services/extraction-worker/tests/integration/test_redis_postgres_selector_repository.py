"""Tests d'intégration de RedisPostgresSelectorRepository.

Contre un vrai Redis (db=14, dédié aux tests du Worker - db=15 est déjà
utilisé par les tests de l'API Gateway, voir Cycle 8) et SQLite en mémoire
comme substitut de test pour PostgreSQL (même compromis assumé qu'au
Cycle 7, ADR-0008).

Ces tests valident le comportement observable de la stratégie cache-aside,
pas son implémentation interne : on vérifie ce qui est lisible depuis
l'extérieur (Redis contient bien la donnée après un cache miss), pas quelle
méthode privée a été appelée.
"""

import pytest
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from extraction_worker.domain.selector import Selector
from extraction_worker.infrastructure.redis_postgres_selector_repository import (
    RedisPostgresSelectorRepository,
)
from extraction_worker.infrastructure.sql.selector_model import Base

_TEST_REDIS_DB = 14


@pytest.fixture
async def engine() -> AsyncEngine:
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
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


class TestSaveThenGetFromCache:
    async def test_save_selector_makes_it_immediately_readable_from_the_cache(
        self, session: AsyncSession, redis_client: redis.Redis
    ) -> None:
        repository = RedisPostgresSelectorRepository(session=session, redis_client=redis_client)

        await repository.save_selector(
            Selector(domain="books.example", field_name="title", selector_value="h1.title", source="manual")
        )

        cached_raw = await redis_client.get("selector:books.example:title")
        assert cached_raw is not None

        result = await repository.get_active_selector(domain="books.example", field_name="title")
        assert result is not None
        assert result.selector_value == "h1.title"


class TestCacheMissFallsBackToPostgresAndWarmsCache:
    async def test_reads_from_postgres_and_populates_redis_when_cache_is_empty(
        self, session: AsyncSession, redis_client: redis.Redis
    ) -> None:
        # Écrit directement en base via un premier repository, PUIS vide le
        # cache Redis manuellement pour simuler un vrai cache miss (ex: Redis
        # redémarré alors que PostgreSQL conserve l'historique).
        writer_repository = RedisPostgresSelectorRepository(session=session, redis_client=redis_client)
        await writer_repository.save_selector(
            Selector(domain="books.example", field_name="price", selector_value=".price", source="manual")
        )
        await redis_client.flushdb()
        assert await redis_client.get("selector:books.example:price") is None

        reader_repository = RedisPostgresSelectorRepository(session=session, redis_client=redis_client)
        result = await reader_repository.get_active_selector(domain="books.example", field_name="price")

        assert result is not None
        assert result.selector_value == ".price"

        # Le cache doit avoir été réchauffé par la lecture qui vient de se produire
        rewarmed = await redis_client.get("selector:books.example:price")
        assert rewarmed is not None


class TestSavingANewVersionUpdatesBothStores:
    async def test_new_version_is_reflected_in_both_postgres_and_redis(
        self, session: AsyncSession, redis_client: redis.Redis
    ) -> None:
        repository = RedisPostgresSelectorRepository(session=session, redis_client=redis_client)

        await repository.save_selector(
            Selector(domain="books.example", field_name="price", selector_value=".v1", source="manual")
        )
        await repository.save_selector(
            Selector(domain="books.example", field_name="price", selector_value=".v2", source="ai_generated")
        )

        result = await repository.get_active_selector(domain="books.example", field_name="price")
        assert result is not None
        assert result.selector_value == ".v2"
        assert result.version == 2
        assert result.source == "ai_generated"


class TestGetActiveSelectorReturnsNoneWhenNothingExists:
    async def test_returns_none_when_neither_cache_nor_postgres_have_the_selector(
        self, session: AsyncSession, redis_client: redis.Redis
    ) -> None:
        repository = RedisPostgresSelectorRepository(session=session, redis_client=redis_client)

        result = await repository.get_active_selector(domain="unknown.example", field_name="title")

        assert result is None


class TestSelectorCacheMetrics:
    """Vérifie l'instrumentation du cache hit/miss (Phase 10), via delta -
    le registre Prometheus est global au process."""

    async def test_records_a_cache_hit(self, session: AsyncSession, redis_client: redis.Redis) -> None:
        from sentinel_shared.observability.metrics import SELECTOR_CACHE_RESULT_TOTAL

        repository = RedisPostgresSelectorRepository(session=session, redis_client=redis_client)
        await repository.save_selector(
            Selector(domain="cache-metrics.example", field_name="title", selector_value="h1", source="manual")
        )

        before = SELECTOR_CACHE_RESULT_TOTAL.labels(result="hit")._value.get()
        await repository.get_active_selector(domain="cache-metrics.example", field_name="title")
        after = SELECTOR_CACHE_RESULT_TOTAL.labels(result="hit")._value.get()

        assert after == before + 1

    async def test_records_a_cache_miss(self, session: AsyncSession, redis_client: redis.Redis) -> None:
        from sentinel_shared.observability.metrics import SELECTOR_CACHE_RESULT_TOTAL

        repository = RedisPostgresSelectorRepository(session=session, redis_client=redis_client)

        before = SELECTOR_CACHE_RESULT_TOTAL.labels(result="miss")._value.get()
        await repository.get_active_selector(domain="never-cached.example", field_name="title")
        after = SELECTOR_CACHE_RESULT_TOTAL.labels(result="miss")._value.get()

        assert after == before + 1
