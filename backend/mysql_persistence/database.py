"""Async SQLAlchemy engine and session lifecycle."""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from .config import MySQLSettings

@dataclass
class DatabaseRuntime:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]

    async def ping(self) -> bool:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True

    async def dispose(self) -> None:
        await self.engine.dispose()

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.sessions() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

def create_database_runtime(settings: MySQLSettings) -> DatabaseRuntime:
    engine = create_async_engine(
        settings.url, pool_pre_ping=True, pool_size=settings.pool_size,
        max_overflow=settings.max_overflow, pool_timeout=settings.pool_timeout,
        pool_recycle=settings.pool_recycle, echo=False,
    )
    sessions = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False,
    )
    return DatabaseRuntime(engine=engine, sessions=sessions)
