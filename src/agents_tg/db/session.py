"""Async database session management."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.agents_tg.config import get_settings
from src.agents_tg.config.settings import normalize_database_url


def _neon_ssl_connect_args(database_url: str) -> dict[str, Any]:
    """asyncpg needs ssl=True for Neon; libpq sslmode= must not reach connect()."""
    lower = database_url.lower()
    if "neon.tech" in lower or "sslmode=require" in lower or "sslmode=verify" in lower:
        return {"ssl": True}
    return {}


def create_engine(db_url: str | None = None, **kwargs: Any):
    """Create async SQLAlchemy engine from settings or custom URL."""
    settings = get_settings()
    raw = db_url or settings.DATABASE_URL
    url = normalize_database_url(raw) if db_url else settings.async_database_url
    connect_args = {**_neon_ssl_connect_args(raw), **kwargs.pop("connect_args", {})}
    if connect_args:
        kwargs["connect_args"] = connect_args
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
