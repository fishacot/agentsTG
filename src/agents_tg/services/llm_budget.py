"""Soft per-user daily LLM call budget (Groq TPM mitigation)."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LLMBudget:
    """Count successful LLM calls per user per UTC day; optional Redis."""

    def __init__(self) -> None:
        self._counts: dict[str, tuple[str, int]] = {}
        self._redis: Any | None = None
        self._redis_checked = False

    def _day_key(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

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

    def _limit(self) -> int:
        from src.agents_tg.config.settings import get_settings

        return int(getattr(get_settings(), "LLM_SOFT_DAILY_CALLS", 0) or 0)

    async def get_usage(self, user_id: str) -> tuple[int, int]:
        """Return (used_today, limit); limit 0 means disabled."""
        limit = self._limit()
        if limit <= 0:
            return 0, 0
        day = self._day_key()
        redis = await self._redis_client()
        key = f"llm_budget:{user_id}:{day}"
        if redis:
            try:
                raw = await redis.get(key)
                return int(raw or 0), limit
            except Exception:
                pass
        stored_day, count = self._counts.get(user_id, (day, 0))
        if stored_day != day:
            return 0, limit
        return count, limit

    async def is_exhausted(self, user_id: str) -> bool:
        used, limit = await self.get_usage(user_id)
        return limit > 0 and used >= limit

    async def record(self, user_id: str) -> None:
        limit = self._limit()
        if limit <= 0:
            return
        day = self._day_key()
        redis = await self._redis_client()
        key = f"llm_budget:{user_id}:{day}"
        if redis:
            try:
                pipe = redis.pipeline()
                await pipe.incr(key)
                await pipe.expire(key, 86400 * 2)
                await pipe.execute()
                return
            except Exception:
                logger.debug("Redis llm budget incr failed")
        stored_day, count = self._counts.get(user_id, (day, 0))
        if stored_day != day:
            count = 0
        self._counts[user_id] = (day, count + 1)

    async def should_force_light_tier(self, user_id: str) -> bool:
        from src.agents_tg.config.settings import get_settings

        if not getattr(get_settings(), "GROQ_DEFER_HEAVY_ON_BUDGET", True):
            return False
        used, limit = await self.get_usage(user_id)
        if limit <= 0:
            return False
        return used >= int(limit * 0.85)


llm_budget = LLMBudget()


def cap_plan_steps(steps: list[str]) -> tuple[list[str], bool]:
    """Trim orchestrator plan to MAX_PLAN_STEPS (resource guardrail)."""
    from src.agents_tg.config.settings import get_settings

    settings = get_settings()
    limit = max(2, int(getattr(settings, "MAX_PLAN_STEPS", 4) or 4))
    if len(steps) <= limit:
        return list(steps), False
    return list(steps[:limit]), True


def max_tokens_for_tier(
    tier: Any,
    *,
    profile_cap: int,
    requested: int,
) -> int:
    from src.agents_tg.config.settings import get_settings
    from src.agents_tg.services.prompts.tier_rules import PromptTier

    settings = get_settings()
    if tier == PromptTier.LIGHT:
        return min(requested, profile_cap, 512)
    if tier == PromptTier.STANDARD:
        return min(requested, profile_cap, 640)
    full_cap = int(getattr(settings, "MAX_TOKENS_FULL_TIER", 900) or 900)
    return min(requested, profile_cap, full_cap)
