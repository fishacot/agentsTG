"""Inbound message pipeline: debounce, dedupe, per-chat lock, followup queue."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

Handler = Callable[..., Awaitable[Any]]


@dataclass
class _PendingBatch:
    texts: list[str] = field(default_factory=list)
    message_ids: list[int] = field(default_factory=list)
    last_message: Any = None
    task: asyncio.Task | None = None


@dataclass
class _FollowupItem:
    message: Any
    handler: Handler
    combined_text: str | None = None


class MessagePipeline:
    """OpenClaw-style inbound debounce + dedupe + per-chat serialization."""

    def __init__(
        self,
        debounce_ms: int = 2000,
        dedupe_ttl_sec: int = 300,
        run_lock_ttl_sec: int = 600,
    ) -> None:
        self.debounce_sec = debounce_ms / 1000.0
        self.dedupe_ttl_sec = dedupe_ttl_sec
        self.run_lock_ttl_sec = run_lock_ttl_sec
        self._seen: dict[str, float] = {}
        self._chat_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._batches: dict[str, _PendingBatch] = {}
        self._busy: dict[str, bool] = {}
        self._followups: dict[str, list[_FollowupItem]] = defaultdict(list)
        self._redis = None
        self._redis_checked = False

    def _dedupe_key(self, agent_key: str, chat_id: int, message_id: int) -> str:
        return f"{agent_key}:{chat_id}:{message_id}"

    def _batch_key(self, agent_key: str, chat_id: int, user_id: int) -> str:
        return f"{agent_key}:{chat_id}:{user_id}"

    def _run_key(self, agent_key: str, chat_id: int) -> str:
        return f"{agent_key}:{chat_id}"

    async def _get_redis(self):
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        try:
            from src.agents_tg.config.settings import get_settings

            url = get_settings().REDIS_URL
            if not url:
                return None
            import redis.asyncio as aioredis

            client = aioredis.from_url(url, decode_responses=True)
            await client.ping()
            self._redis = client
        except Exception as exc:
            logger.debug("Redis unavailable for pipeline: %s", exc)
            self._redis = None
        return self._redis

    async def is_duplicate(self, agent_key: str, chat_id: int, message_id: int) -> bool:
        key = self._dedupe_key(agent_key, chat_id, message_id)
        now = time.time()

        redis = await self._get_redis()
        if redis:
            try:
                ok = await redis.set(
                    f"dedupe:{key}", "1", nx=True, ex=self.dedupe_ttl_sec
                )
                return ok is None
            except Exception:
                pass

        expired = [k for k, t in self._seen.items() if now - t > self.dedupe_ttl_sec]
        for k in expired:
            del self._seen[k]
        if key in self._seen:
            return True
        self._seen[key] = now
        return False

    def chat_lock(self, agent_key: str, chat_id: int) -> asyncio.Lock:
        return self._chat_locks[f"{agent_key}:{chat_id}"]

    def is_busy(self, agent_key: str, chat_id: int) -> bool:
        return self._busy.get(self._run_key(agent_key, chat_id), False)

    def queue_followup(
        self,
        *,
        agent_key: str,
        message: Any,
        handler: Handler,
        combined_text: str | None = None,
    ) -> None:
        """Queue message while chat is processing."""
        key = self._run_key(agent_key, message.chat.id)
        self._followups[key].append(
            _FollowupItem(message=message, handler=handler, combined_text=combined_text)
        )
        logger.debug("Followup queued for %s (depth=%s)", key, len(self._followups[key]))

    async def drain_followups(self, agent_key: str, chat_id: int) -> None:
        """Process one queued followup after current run completes."""
        key = self._run_key(agent_key, chat_id)
        items = self._followups.get(key, [])
        if not items:
            return
        item = items.pop(0)
        if not items:
            self._followups.pop(key, None)
        await item.handler(item.message, combined_text=item.combined_text)

    @asynccontextmanager
    async def run_lock(self, agent_key: str, chat_id: int):
        """Per-chat run lock (Redis NX + local asyncio lock)."""
        key = self._run_key(agent_key, chat_id)
        redis = await self._get_redis()
        redis_key = f"runlock:{agent_key}:{chat_id}"

        if redis:
            try:
                acquired = await redis.set(
                    redis_key, "1", nx=True, ex=self.run_lock_ttl_sec
                )
                if not acquired:
                    raise RuntimeError("run_lock_busy")
            except RuntimeError:
                raise
            except Exception:
                pass

        self._busy[key] = True
        async with self.chat_lock(agent_key, chat_id):
            try:
                yield
            finally:
                self._busy[key] = False
                if redis:
                    try:
                        await redis.delete(redis_key)
                    except Exception:
                        pass

    async def enqueue_debounced(
        self,
        *,
        agent_key: str,
        message: Any,
        handler: Handler,
    ) -> None:
        """Debounce rapid messages from same user in same chat."""
        chat_id = message.chat.id
        user_id = message.from_user.id if message.from_user else 0
        batch_key = self._batch_key(agent_key, chat_id, user_id)
        text = (message.text or "").strip()

        batch = self._batches.get(batch_key)
        if batch is None:
            batch = _PendingBatch()
            self._batches[batch_key] = batch

        batch.texts.append(text)
        batch.message_ids.append(message.message_id)
        batch.last_message = message

        if batch.task and not batch.task.done():
            batch.task.cancel()

        async def _flush() -> None:
            await asyncio.sleep(self.debounce_sec)
            b = self._batches.pop(batch_key, None)
            if not b or not b.last_message:
                return
            combined = "\n".join(t for t in b.texts if t)
            if self.is_busy(agent_key, chat_id):
                self.queue_followup(
                    agent_key=agent_key,
                    message=b.last_message,
                    handler=handler,
                    combined_text=combined or None,
                )
                return
            async with self.run_lock(agent_key, chat_id):
                await handler(b.last_message, combined_text=combined or None)
                await self.drain_followups(agent_key, chat_id)

        batch.task = asyncio.create_task(_flush())


message_pipeline = MessagePipeline()
