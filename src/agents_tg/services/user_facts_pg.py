"""Postgres persistence for user facts (Mem0 fallback)."""

from __future__ import annotations

import logging

from sqlalchemy import select

from src.agents_tg.db.models import UserFact
from src.agents_tg.db.session import create_engine, create_session_factory

logger = logging.getLogger(__name__)

_engine = None
_factory = None


def _session_factory():
    global _engine, _factory
    if _factory is None:
        _engine = create_engine()
        _factory = create_session_factory(_engine)
    return _factory


async def persist_user_fact(
    *,
    telegram_user_id: int,
    fact: str,
    agent_key: str | None = None,
    category: str | None = None,
) -> None:
    factory = _session_factory()
    async with factory() as session:
        existing = await session.execute(
            select(UserFact).where(
                UserFact.telegram_user_id == telegram_user_id,
                UserFact.fact == fact,
            )
        )
        if existing.scalar_one_or_none():
            return
        session.add(
            UserFact(
                telegram_user_id=telegram_user_id,
                fact=fact,
                agent_key=agent_key,
                category=category,
            )
        )
        await session.commit()


async def get_user_facts(
    *,
    telegram_user_id: int,
    limit: int = 100,
) -> list[str]:
    factory = _session_factory()
    async with factory() as session:
        stmt = (
            select(UserFact.fact)
            .where(UserFact.telegram_user_id == telegram_user_id)
            .order_by(UserFact.id.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(reversed([row[0] for row in result.all()]))
