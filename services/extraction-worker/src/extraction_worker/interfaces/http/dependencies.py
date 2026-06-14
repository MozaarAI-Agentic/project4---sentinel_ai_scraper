"""Composition root de l'Extraction Worker.

Les deux ports (BrowserPort, SelectorRepositoryPort) sont désormais câblés
vers de vraies implémentations - aucun NotImplementedError ne subsiste.
"""

from collections.abc import AsyncGenerator

import redis.asyncio as redis
from fastapi import Request

from extraction_worker.domain.ports.browser_port import BrowserPort
from extraction_worker.domain.ports.selector_repository_port import SelectorRepositoryPort
from extraction_worker.infrastructure.playwright_browser import PlaywrightBrowser
from extraction_worker.infrastructure.redis_postgres_selector_repository import (
    RedisPostgresSelectorRepository,
)


def get_browser(request: Request) -> BrowserPort:
    return PlaywrightBrowser(headless=True)


async def get_selector_repository(
    request: Request,
) -> AsyncGenerator[SelectorRepositoryPort, None]:
    session_factory = request.app.state.db_session_factory
    redis_client: redis.Redis = request.app.state.redis_client
    async with session_factory() as session:
        yield RedisPostgresSelectorRepository(session=session, redis_client=redis_client)
