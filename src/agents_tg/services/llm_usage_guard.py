"""Soft daily LLM call budget per user (Redis or memory)."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LLMUsageGuard:
    def __init__(self) -> None:
        self._counts: dict[str, tuple[str, int]] = {}
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

    def _day_key(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    async def check(self, user_id: str) -> tuple[bool, str]:
        from src.agents_tg.config.settings import get_settings

        cap = int(get_settings().LLM_DAILY_SOFT_CAP or 0)
        if cap <= 0:
            return True, ""
        day = self._day_key()
        key = f"llm_use:{user_id}:{day}"
        redis = await self._redis_client()
        count = 0
        if redis:
            try:
                raw = await redis.get(key)
                count = int(raw or 0)
            except Exception:
                pass
        else:
            stored = self._counts.get(user_id)
            if stored and stored[0] == day:
                count = stored[1]
        if count >= cap:
            return (
                False,
                f"Дневной лимит AI ({cap} запросов). Продолжим завтра или уточните одним коротким сообщением.",
            )
        return True, ""

    async def record(self, user_id: str) -> None:
        from src.agents_tg.config.settings import get_settings

        cap = int(get_settings().LLM_DAILY_SOFT_CAP or 0)
        if cap <= 0:
            return
        day = self._day_key()
        key = f"llm_use:{user_id}:{day}"
        redis = await self._redis_client()
        if redis:
            try:
                pipe = redis.pipeline()
                await pipe.incr(key)
                await pipe.expire(key, 86400 * 2)
                await pipe.execute()
                return
            except Exception:
                pass
        prev = self._counts.get(user_id)
        n = (prev[1] + 1) if prev and prev[0] == day else 1
        self._counts[user_id] = (day, n)


llm_usage_guard = LLMUsageGuard()
