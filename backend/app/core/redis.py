import redis.asyncio as aioredis

from app.core.config import settings


class RedisClient:
    def __init__(self):
        self._redis = None

    async def initialize(self):
        self._redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

    async def close(self):
        if self._redis:
            await self._redis.close()

    @property
    def client(self):
        return self._redis

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        await self._redis.set(key, value, ex=ex)

    async def delete(self, key: str):
        await self._redis.delete(key)

    async def delete_by_pattern(self, pattern: str) -> int:
        """Delete all keys matching a glob-style pattern (e.g. todos:user:{id}:*)."""
        deleted = 0
        async for key in self._redis.scan_iter(match=pattern):
            await self._redis.delete(key)
            deleted += 1
        return deleted

    async def exists(self, key: str) -> bool:
        return await self._redis.exists(key)

    async def ping(self) -> bool:
        """Check connectivity without exposing connection errors to callers."""

        if self._redis is None:
            return False
        try:
            return bool(await self._redis.ping())
        except Exception:
            return False


redis_client = RedisClient()
