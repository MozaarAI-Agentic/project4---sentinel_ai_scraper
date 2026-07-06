"""Pre-seeds the guided demo's known-correct `title` selector, deliberately
leaving `price` unknown so the first request always triggers a real,
reproducible AI recovery cycle. See ADR-0017.
"""

import asyncio
import os

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from extraction_worker.domain.selector import Selector
from extraction_worker.infrastructure.redis_postgres_selector_repository import (
    RedisPostgresSelectorRepository,
)
from extraction_worker.infrastructure.sql.selector_model import Base

DEMO_DOMAIN = "demo.sentinelai.local"


async def seed() -> None:
    database_url = os.environ["DATABASE_URL"]
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    redis_client = redis.from_url(redis_url, decode_responses=True)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        repository = RedisPostgresSelectorRepository(session=session, redis_client=redis_client)
        await repository.save_selector(
            Selector(domain=DEMO_DOMAIN, field_name="title", selector_value="h1.title", source="manual")
        )

    await redis_client.aclose()
    await engine.dispose()
    print(f"Seeded 'title' selector for {DEMO_DOMAIN} - 'price' intentionally left unknown")


if __name__ == "__main__":
    asyncio.run(seed())
