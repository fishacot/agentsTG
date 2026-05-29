"""Per-user per-agent chat history (in-memory, Redis, or Postgres)."""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

MAX_TURNS = 20
MAX_MESSAGE_LEN = 2000


@dataclass
class ChatTurn:
    role: str
    content: str


class ChatHistoryStore:
    """Store recent dialogue turns for context continuity."""

    def __init__(self) -> None:
        self._memory: dict[str, deque[ChatTurn]] = {}
        self._redis: Any | None = None
        self._redis_checked = False
        self._pg_available = False

    def set_pg_available(self, available: bool) -> None:
        self._pg_available = available

    def _key(self, user_id: str, agent_key: str) -> str:
        return f"chat:{user_id}:{agent_key}"

    async def _get_redis(self) -> Any | None:
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        try:
            from src.agents_tg.config.settings import get_settings

            url = get_settings().REDIS_URL
            if not url:
                self._redis = None
                return None
            import redis.asyncio as aioredis

            client = aioredis.from_url(url, decode_responses=True)
            await client.ping()
            self._redis = client
            logger.info("Chat history using Redis")
        except Exception as exc:
            logger.debug("Redis unavailable for chat history: %s", exc)
            self._redis = None
        return self._redis

    async def append(
        self,
        user_id: str,
        agent_key: str,
        role: str,
        content: str,
    ) -> None:
        text = (content or "")[:MAX_MESSAGE_LEN]
        if not text:
            return
        turn = ChatTurn(role=role, content=text)
        key = self._key(user_id, agent_key)

        if key not in self._memory:
            self._memory[key] = deque(maxlen=MAX_TURNS * 2)
        self._memory[key].append(turn)

        redis = await self._get_redis()
        if redis:
            try:
                payload = json.dumps({"role": role, "content": text}, ensure_ascii=False)
                await redis.rpush(key, payload)
                await redis.ltrim(key, -MAX_TURNS * 2, -1)
            except Exception as exc:
                logger.warning("Redis chat history append failed: %s", exc)

        if self._pg_available:
            try:
                from src.agents_tg.services.chat_history_pg import append_message_pg

                await append_message_pg(
                    telegram_user_id=int(user_id),
                    agent_key=agent_key,
                    role=role,
                    content=text,
                )
            except Exception as exc:
                logger.warning("Postgres chat history append failed: %s", exc)

    async def get_recent(
        self,
        user_id: str,
        agent_key: str,
        limit: int = MAX_TURNS,
    ) -> list[ChatTurn]:
        key = self._key(user_id, agent_key)
        redis = await self._get_redis()
        if redis:
            try:
                raw = await redis.lrange(key, -limit * 2, -1)
                if raw:
                    turns = []
                    for item in raw:
                        data = json.loads(item)
                        turns.append(
                            ChatTurn(role=data["role"], content=data["content"])
                        )
                    return turns[-limit * 2 :]
            except Exception as exc:
                logger.debug("Redis chat history read failed: %s", exc)

        if self._pg_available:
            try:
                from src.agents_tg.services.chat_history_pg import get_recent_pg

                return await get_recent_pg(
                    telegram_user_id=int(user_id),
                    agent_key=agent_key,
                    limit=limit * 2,
                )
            except Exception as exc:
                logger.debug("Postgres chat history read failed: %s", exc)

        mem = self._memory.get(key, deque())
        return list(mem)[-limit * 2 :]

    def format_for_prompt(self, turns: list[ChatTurn]) -> str:
        if not turns:
            return ""
        lines = []
        for t in turns:
            label = "Пользователь" if t.role == "user" else "Ассистент"
            lines.append(f"{label}: {t.content[:500]}")
        return "\n".join(lines)


chat_history = ChatHistoryStore()
