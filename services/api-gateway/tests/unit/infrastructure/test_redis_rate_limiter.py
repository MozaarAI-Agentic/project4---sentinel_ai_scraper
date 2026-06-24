"""Tests de RedisRateLimiter.

Le compteur est testé par nombre d'appels, pas par temps réel écoulé -
évite de dépendre de freezegun ou d'un vrai sleep() pour tester
l'expiration de fenêtre.
"""

import redis.asyncio as redis
import pytest

from api_gateway.infrastructure.redis_rate_limiter import RedisRateLimiter

_TEST_REDIS_DB = 12


@pytest.fixture
async def redis_client() -> redis.Redis:
    client = redis.Redis(host="localhost", port=6379, db=_TEST_REDIS_DB, decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


class TestRedisRateLimiterAllowsWithinLimit:
    async def test_allows_requests_up_to_the_limit(self, redis_client: redis.Redis) -> None:
        limiter = RedisRateLimiter(redis_client=redis_client, limit=3, window_seconds=60)

        results = [await limiter.is_allowed("1.2.3.4") for _ in range(3)]

        assert results == [True, True, True]

    async def test_rejects_the_request_beyond_the_limit(self, redis_client: redis.Redis) -> None:
        limiter = RedisRateLimiter(redis_client=redis_client, limit=3, window_seconds=60)

        for _ in range(3):
            await limiter.is_allowed("1.2.3.4")
        fourth = await limiter.is_allowed("1.2.3.4")

        assert fourth is False


class TestRedisRateLimiterIsolatesIdentifiers:
    async def test_limit_is_tracked_independently_per_identifier(
        self, redis_client: redis.Redis
    ) -> None:
        limiter = RedisRateLimiter(redis_client=redis_client, limit=1, window_seconds=60)

        first_ip_first_call = await limiter.is_allowed("1.1.1.1")
        second_ip_first_call = await limiter.is_allowed("2.2.2.2")

        assert first_ip_first_call is True
        assert second_ip_first_call is True  # IP différente, compteur différent


class TestRedisRateLimiterSetsExpiration:
    async def test_sets_a_ttl_on_the_counter_key(self, redis_client: redis.Redis) -> None:
        limiter = RedisRateLimiter(redis_client=redis_client, limit=5, window_seconds=60)

        await limiter.is_allowed("1.2.3.4")

        ttl = await redis_client.ttl("ratelimit:1.2.3.4")
        assert 0 < ttl <= 60
