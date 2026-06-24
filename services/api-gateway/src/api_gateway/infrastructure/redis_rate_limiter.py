"""Rate limiter à fenêtre fixe, basé sur Redis.

Conçu en Phase 6 (API Design), jamais câblé jusqu'ici - dette comblée
maintenant. `INCR` sur une clé qui expire après `window_seconds` : le
premier appel dans une fenêtre pose le TTL, les suivants l'incrémentent
sans le reposer (sinon la fenêtre ne finirait jamais par expirer sous
trafic constant).
"""

import redis.asyncio as redis


class RedisRateLimiter:
    def __init__(
        self, redis_client: redis.Redis, limit: int = 60, window_seconds: int = 60
    ) -> None:
        self._redis = redis_client
        self._limit = limit
        self._window_seconds = window_seconds

    async def is_allowed(self, identifier: str) -> bool:
        key = f"ratelimit:{identifier}"
        current_count = await self._redis.incr(key)

        if current_count == 1:
            await self._redis.expire(key, self._window_seconds)

        return current_count <= self._limit
