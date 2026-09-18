import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings

logger = logging.getLogger(__name__)

# Fallback local para desarrollo y pruebas si no se define DATABASE_URL
DEFAULT_SQLITE_TEST_URL = "sqlite+aiosqlite:///./test_financial.db"

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the singleton SQLAlchemy AsyncEngine instance.
    
    Initializes the engine on first call using settings.database_url or a fallback.
    """
    global _engine
    if _engine is None:
        db_url = settings.database_url.strip()
        if not db_url:
            logger.warning(
                "DATABASE_URL is not set in environment. Falling back to local SQLite for development: %s",
                DEFAULT_SQLITE_TEST_URL,
            )
            db_url = DEFAULT_SQLITE_TEST_URL
        
        # asyncpg requiere postgresql+asyncpg://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        _engine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the singleton session factory for async sessions."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def init_db() -> None:
    """Initialize all ORM tables using Base.metadata."""
    from db.base import Base
    import db.models  # noqa: F401
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI and tools dependency that yields an asynchronous database session.
    
    Ensures transaction rollback on error and proper closing of the session.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception as err:
            await session.rollback()
            logger.error("Database session rolled back due to error: %s", err)
            raise
        finally:
            await session.close()
