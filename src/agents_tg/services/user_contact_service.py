"""Track last DM contact for proactive wake and digest delivery."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class _MemContact:
    telegram_user_id: int
    chat_id: int
    agent_key: str
    last_inbound_at: datetime
    last_outbound_at: datetime | None = None
    last_heartbeat_at: datetime | None = None


class UserContactService:
    """Registry of users eligible for proactive agent wake."""

    def __init__(self) -> None:
        self._memory: dict[tuple[int, str], _MemContact] = {}
        self._pg_engine: Any | None = None

    def set_pg_engine(self, engine: Any) -> None:
        self._pg_engine = engine

    async def record_inbound(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        agent_key: str = "personal_assistant",
    ) -> None:
        now = datetime.now(timezone.utc)
        if self._pg_engine:
            await self._upsert_pg(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                agent_key=agent_key,
                last_inbound_at=now,
            )
        else:
            key = (telegram_user_id, agent_key)
            self._memory[key] = _MemContact(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                agent_key=agent_key,
                last_inbound_at=now,
                last_outbound_at=self._memory.get(key).last_outbound_at
                if key in self._memory
                else None,
                last_heartbeat_at=self._memory.get(key).last_heartbeat_at
                if key in self._memory
                else None,
            )

    async def record_outbound(
        self,
        *,
        telegram_user_id: int,
        agent_key: str = "personal_assistant",
    ) -> None:
        now = datetime.now(timezone.utc)
        if self._pg_engine:
            await self._touch_outbound_pg(telegram_user_id, agent_key, now)
        else:
            key = (telegram_user_id, agent_key)
            if key in self._memory:
                self._memory[key].last_outbound_at = now

    async def record_heartbeat(
        self,
        *,
        telegram_user_id: int,
        agent_key: str = "personal_assistant",
    ) -> None:
        now = datetime.now(timezone.utc)
        if self._pg_engine:
            await self._touch_heartbeat_pg(telegram_user_id, agent_key, now)
        else:
            key = (telegram_user_id, agent_key)
            if key in self._memory:
                self._memory[key].last_heartbeat_at = now

    async def list_wake_candidates(
        self, *, agent_key: str = "personal_assistant"
    ) -> list[dict[str, Any]]:
        if self._pg_engine:
            return await self._list_pg(agent_key)
        return [
            {
                "telegram_user_id": c.telegram_user_id,
                "chat_id": c.chat_id,
                "agent_key": c.agent_key,
                "last_inbound_at": c.last_inbound_at,
                "last_outbound_at": c.last_outbound_at,
                "last_heartbeat_at": c.last_heartbeat_at,
            }
            for c in self._memory.values()
            if c.agent_key == agent_key
        ]

    async def _upsert_pg(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        agent_key: str,
        last_inbound_at: datetime,
    ) -> None:
        from sqlalchemy import select, update
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from src.agents_tg.db.models import UserContact

        async with self._pg_engine.begin() as conn:
            existing = await conn.execute(
                select(UserContact.id).where(
                    UserContact.telegram_user_id == telegram_user_id,
                    UserContact.agent_key == agent_key,
                )
            )
            if existing.first():
                await conn.execute(
                    update(UserContact)
                    .where(
                        UserContact.telegram_user_id == telegram_user_id,
                        UserContact.agent_key == agent_key,
                    )
                    .values(chat_id=chat_id, last_inbound_at=last_inbound_at)
                )
            else:
                await conn.execute(
                    pg_insert(UserContact).values(
                        telegram_user_id=telegram_user_id,
                        chat_id=chat_id,
                        agent_key=agent_key,
                        last_inbound_at=last_inbound_at,
                    )
                )

    async def _touch_outbound_pg(
        self, telegram_user_id: int, agent_key: str, when: datetime
    ) -> None:
        from sqlalchemy import update

        from src.agents_tg.db.models import UserContact

        async with self._pg_engine.begin() as conn:
            await conn.execute(
                update(UserContact)
                .where(
                    UserContact.telegram_user_id == telegram_user_id,
                    UserContact.agent_key == agent_key,
                )
                .values(last_outbound_at=when)
            )

    async def _touch_heartbeat_pg(
        self, telegram_user_id: int, agent_key: str, when: datetime
    ) -> None:
        from sqlalchemy import update

        from src.agents_tg.db.models import UserContact

        async with self._pg_engine.begin() as conn:
            await conn.execute(
                update(UserContact)
                .where(
                    UserContact.telegram_user_id == telegram_user_id,
                    UserContact.agent_key == agent_key,
                )
                .values(last_heartbeat_at=when)
            )

    async def _list_pg(self, agent_key: str) -> list[dict[str, Any]]:
        from sqlalchemy import select

        from src.agents_tg.db.models import UserContact

        async with self._pg_engine.connect() as conn:
            rows = await conn.execute(
                select(UserContact).where(UserContact.agent_key == agent_key)
            )
            return [
                {
                    "telegram_user_id": r.telegram_user_id,
                    "chat_id": r.chat_id,
                    "agent_key": r.agent_key,
                    "last_inbound_at": r.last_inbound_at,
                    "last_outbound_at": r.last_outbound_at,
                    "last_heartbeat_at": r.last_heartbeat_at,
                }
                for r in rows.scalars().all()
            ]


user_contact_service = UserContactService()
