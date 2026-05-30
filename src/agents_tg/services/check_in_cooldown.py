"""24h cooldown for Elza project check-in prompts."""

from __future__ import annotations

import time
from typing import Any


class CheckInCooldown:
    def __init__(self, interval_sec: float = 86400.0) -> None:
        self.interval_sec = interval_sec
        self._last: dict[str, float] = {}
        self._redis: Any | None = None
        self._checked = False

    async def _redis_client(self) -> Any | None:
        if self._checked:
            return self._redis
        self._checked = True
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

    async def should_offer_checkin(self, user_id: str) -> bool:
        key = f"checkin:{user_id}"
        redis = await self._redis_client()
        if redis:
            try:
                if await redis.exists(key):
                    return False
            except Exception:
                pass
        last = self._last.get(user_id, 0.0)
        return (time.time() - last) >= self.interval_sec

    async def record_checkin(self, user_id: str) -> None:
        self._last[user_id] = time.time()
        redis = await self._redis_client()
        if redis:
            try:
                await redis.setex(f"checkin:{user_id}", int(self.interval_sec), "1")
            except Exception:
                pass


check_in_cooldown = CheckInCooldown()
