"""Tests d'intégration de SqlAlchemyJobRepository.

Ces tests utilisent SQLite en mémoire (aiosqlite) comme substitut de test
pour PostgreSQL. Le mapping SQLAlchemy est identique quel que soit le
moteur - seul le driver change. C'est un compromis assumé et documenté
(voir ADR-0008) : les tests unitaires/intégration restent rapides et sans
dépendance Docker, tandis qu'un test end-to-end séparé (marqué
`@pytest.mark.postgres`, à ajouter en Phase 9 - Testing) validera contre un
vrai PostgreSQL avant chaque release.

Placés dans tests/integration/ plutôt que tests/unit/ : ce sont de vrais
tests contre une base de données réelle (même si c'est SQLite), pas des
tests contre des doubles en mémoire.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from api_gateway.domain.job import Job
from api_gateway.infrastructure.sql.job_model import Base
from api_gateway.infrastructure.sql.sqlalchemy_job_repository import SqlAlchemyJobRepository
from sentinel_shared.enums import FailureReason, JobStatus


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async_session = AsyncSession(engine, expire_on_commit=False)
    yield async_session
    await async_session.close()
    await engine.dispose()


class TestSaveAndGetJob:
    async def test_saves_and_retrieves_a_pending_job(self, session: AsyncSession) -> None:
        repository = SqlAlchemyJobRepository(session=session)
        job = Job.create(
            url="https://books.example/1", domain="books.example", required_fields=["title", "price"]
        )

        await repository.save(job)
        retrieved = await repository.get(job.id)

        assert retrieved is not None
        assert retrieved.id == job.id
        assert retrieved.url == "https://books.example/1"
        assert retrieved.domain == "books.example"
        assert retrieved.required_fields == ["title", "price"]
        assert retrieved.status == JobStatus.PENDING
        assert retrieved.result is None
        assert retrieved.failure_reason is None

    async def test_returns_none_for_an_unknown_job_id(self, session: AsyncSession) -> None:
        repository = SqlAlchemyJobRepository(session=session)

        retrieved = await repository.get("does-not-exist")

        assert retrieved is None


class TestSaveUpdatesExistingJob:
    async def test_saving_a_job_with_the_same_id_updates_it_rather_than_duplicating(
        self, session: AsyncSession
    ) -> None:
        repository = SqlAlchemyJobRepository(session=session)
        job = Job.create(url="https://books.example/1", domain="books.example", required_fields=["title"])
        await repository.save(job)

        succeeded_job = job.mark_succeeded(result={"title": "Clean Code"})
        await repository.save(succeeded_job)

        retrieved = await repository.get(job.id)
        assert retrieved is not None
        assert retrieved.status == JobStatus.SUCCESS
        assert retrieved.result == {"title": "Clean Code"}


class TestPersistsFailureReason:
    async def test_persists_and_retrieves_a_failed_job_with_its_reason(
        self, session: AsyncSession
    ) -> None:
        repository = SqlAlchemyJobRepository(session=session)
        job = Job.create(url="https://books.example/1", domain="books.example", required_fields=["title"])
        failed_job = job.mark_failed(failure_reason=FailureReason.NAVIGATION_ERROR)

        await repository.save(failed_job)
        retrieved = await repository.get(job.id)

        assert retrieved is not None
        assert retrieved.status == JobStatus.FAILED
        assert retrieved.failure_reason == FailureReason.NAVIGATION_ERROR
