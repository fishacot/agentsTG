"""Postgres persistence for chat history."""

from __future__ import annotations

import logging

from sqlalchemy import select

from src.agents_tg.db.models import ChatMessage
from src.agents_tg.db.session import create_engine, create_session_factory
from src.agents_tg.services.chat_history import ChatTurn

logger = logging.getLogger(__name__)

_engine = None
_factory = None


def _session_factory():
    global _engine, _factory
    if _factory is None:
        _engine = create_engine()
        _factory = create_session_factory(_engine)
    return _factory


async def append_message_pg(
    *,
    telegram_user_id: int,
    agent_key: str,
    role: str,
    content: str,
) -> None:
    factory = _session_factory()
    async with factory() as session:
        session.add(
            ChatMessage(
                telegram_user_id=telegram_user_id,
                agent_key=agent_key,
                role=role,
                content=content,
            )
        )
        await session.commit()


async def get_recent_pg(
    *,
    telegram_user_id: int,
    agent_key: str,
    limit: int = 40,
) -> list[ChatTurn]:
    factory = _session_factory()
    async with factory() as session:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.telegram_user_id == telegram_user_id,
                ChatMessage.agent_key == agent_key,
            )
            .order_by(ChatMessage.id.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = list(reversed(result.scalars().all()))
        return [ChatTurn(role=r.role, content=r.content) for r in rows]
