"""Database configuration, async SQLAlchemy engine, and session management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from syntra.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base declarative class for all SYNTRA models."""
    pass


class DatabaseManager:
    """Manages async database engine and connection pool."""

    def __init__(self, database_url: str | None = None) -> None:
        self.url = database_url or get_settings().database_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def get_engine(self) -> AsyncEngine:
        """Get or initialize AsyncEngine."""
        if self._engine is None:
            connect_args = {}
            if "sqlite" in self.url:
                connect_args["check_same_thread"] = False

            self._engine = create_async_engine(
                self.url,
                echo=False,
                future=True,
                connect_args=connect_args,
            )
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
                autoflush=False,
            )
        return self._engine

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get session factory."""
        if self._session_factory is None:
            self.get_engine()
        assert self._session_factory is not None
        return self._session_factory

    async def init_tables(self) -> None:
        """Create database tables if they do not exist."""
        engine = self.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully for %s", self.url)

    async def drop_tables(self) -> None:
        """Drop all tables (used in test cleanups)."""
        engine = self.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager yielding a transactional database session."""
        factory = self.get_session_factory()
        async with factory() as sess:
            try:
                yield sess
                await sess.commit()
            except Exception:
                await sess.rollback()
                raise

    async def close(self) -> None:
        """Dispose database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Retrieve global DatabaseManager singleton."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
