"""Async database session management."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.agents_tg.config import get_settings


def create_engine(db_url: str | None = None, **kwargs: Any):
    """Create async SQLAlchemy engine from settings or custom URL."""
    settings = get_settings()
    url = db_url or settings.async_database_url
    return create_async_engine(url, **kwargs)


def create_session_factory(engine=None, **kwargs: Any):
    """Create async session factory."""
    if engine is None:
        engine = create_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        **kwargs,
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: provide an async database session."""
    engine = create_engine()
    factory = create_session_factory(engine)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
