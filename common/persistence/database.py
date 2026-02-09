"""Async SQLite database engine via aiosqlite + SQLModel."""

from __future__ import annotations

from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

_engine = None
_async_session_factory = None


async def init_db(db_url: str = "sqlite+aiosqlite:///data/scraper.db") -> None:
    """Initialize the async database engine and create all tables."""
    global _engine, _async_session_factory

    # Ensure the data directory exists for SQLite files
    if "sqlite" in db_url:
        db_path = db_url.split("///")[-1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _engine = create_async_engine(db_url, echo=False)
    _async_session_factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """Dispose of the database engine."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _async_session_factory() as session:
        yield session
