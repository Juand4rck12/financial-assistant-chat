import os
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Forzar base de datos SQLite aislada en memoria para la ejecución de pruebas
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import db.connection as db_conn
from db.base import Base


@pytest.fixture(autouse=True)
async def isolate_db_for_testing(monkeypatch):
    """Ensure every test runs against a clean, isolated in-memory database."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    test_session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    # Crear todas las tablas en la memoria de pruebas
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Reemplazar el engine y factory global durante el test
    monkeypatch.setattr(db_conn, "_engine", test_engine)
    monkeypatch.setattr(db_conn, "_session_factory", test_session_factory)
    monkeypatch.setattr(db_conn, "get_engine", lambda: test_engine)
    monkeypatch.setattr(db_conn, "get_session_factory", lambda: test_session_factory)

    # Dependency override para FastAPI get_db_session
    async def override_get_db_session():
        async with test_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    from main import app
    app.dependency_overrides[db_conn.get_db_session] = override_get_db_session

    yield

    app.dependency_overrides.clear()
    await test_engine.dispose()
