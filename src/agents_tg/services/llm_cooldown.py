"""Per-user LLM request cooldown to reduce Groq 429."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LLMCooldown:
    """Minimum interval between LLM calls per Telegram user."""

    def __init__(self, interval_sec: float | None = None) -> None:
        self.interval_sec = interval_sec
        self._last: dict[str, float] = {}
        self._redis: Any | None = None
        self._redis_checked = False

    async def _redis_client(self) -> Any | None:
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        try:
            from src.agents_tg.config.settings import get_settings

            url = get_settings().REDIS_URL
            if not url:
                return None
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(url, decode_responses=True)
            await self._redis.ping()
        except Exception:
            self._redis = None
        return self._redis

    async def check(self, user_id: str) -> tuple[bool, int]:
        """Return (allowed, seconds_to_wait)."""
        from src.agents_tg.config.settings import get_settings

        interval = self.interval_sec
        if interval is None:
            interval = get_settings().LLM_COOLDOWN_SEC
        now = time.time()
        redis = await self._redis_client()
        key = f"llm_cd:{user_id}"

        if redis:
            try:
                ttl = await redis.ttl(key)
                if ttl and ttl > 0:
                    return False, int(ttl)
            except Exception:
                pass

        last = self._last.get(user_id, 0.0)
        elapsed = now - last
        if elapsed < interval:
            return False, max(1, int(interval - elapsed) + 1)
        return True, 0

    async def record(self, user_id: str) -> None:
        from src.agents_tg.config.settings import get_settings

        interval = self.interval_sec
        if interval is None:
            interval = get_settings().LLM_COOLDOWN_SEC
        now = time.time()
        self._last[user_id] = now
        redis = await self._redis_client()
        if redis:
            try:
                await redis.setex(
                    f"llm_cd:{user_id}",
                    int(interval) + 1,
                    "1",
                )
            except Exception:
                pass


llm_cooldown = LLMCooldown()
