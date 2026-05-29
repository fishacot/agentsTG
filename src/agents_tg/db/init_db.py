"""Database schema initialization."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncEngine

from src.agents_tg.db.base import Base

logger = logging.getLogger(__name__)


async def init_db(engine: AsyncEngine) -> None:
    """Create all tables if they do not exist."""
    import src.agents_tg.db.models  # noqa: F401 — register ORM models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")
