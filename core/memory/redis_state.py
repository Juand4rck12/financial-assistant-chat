import logging
from typing import Optional
from core.config import settings

logger = logging.getLogger(__name__)


class RedisStateManager:
    """Manages ephemeral WhatsApp user locks and conversation caches."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url
        self._client = None

    async def connect(self):
        """Establish async Redis connection if URL is configured."""
        if self.redis_url and not self._client:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(self.redis_url, decode_responses=True)
                await self._client.ping()
                logger.info("Connected to Redis at %s", self.redis_url)
            except Exception as e:
                logger.warning("Could not connect to Redis (%s). Operating without Redis cache.", e)
                self._client = None

    async def acquire_lock(self, phone_number: str, timeout_seconds: int = 10) -> bool:
        """Acquire a temporary lock per phone number to serialize rapid WhatsApp messages."""
        if not self._client:
            return True
        try:
            lock_key = f"lock:user:{phone_number}"
            acquired = await self._client.set(lock_key, "1", nx=True, ex=timeout_seconds)
            return bool(acquired)
        except Exception as e:
            logger.error("Error acquiring Redis lock for %s: %s", phone_number, e)
            return True

    async def release_lock(self, phone_number: str):
        """Release the temporary user lock."""
        if not self._client:
            return
        try:
            lock_key = f"lock:user:{phone_number}"
            await self._client.delete(lock_key)
        except Exception as e:
            logger.error("Error releasing Redis lock for %s: %s", phone_number, e)

    async def close(self):
        if self._client:
            await self._client.close()


redis_manager = RedisStateManager()
