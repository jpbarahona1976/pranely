"""Pytest configuration and fixtures for tests."""
import os
from typing import AsyncGenerator

# Set required environment variables BEFORE importing app modules
# This is required because app.core.config runs get_settings() at module load time
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32chars")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ENV", "test")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app

# Use SQLite for tests (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    # Import here to avoid circular imports
    from app.models import Base
    
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
    
    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db(db_session: AsyncSession) -> AsyncSession:
    """Alias for db_session for compatibility."""
    return db_session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database session override."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def app_client(client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    """Alias for client fixture for test compatibility."""
    yield client


# =============================================================================
# Table Cleanup Fixture (IntegrityError Fix)
# =============================================================================
# Tables that need to be truncated between tests to avoid duplicate key errors
CRITICAL_TABLES = [
    "users",
    "organizations",
    "memberships",
    "employers",
    "transporters",
    "residues",
    "employer_transporter_links",
    "audit_trails",
    "waste_movements",  # FASE 5B: Waste movements table
]


@pytest_asyncio.fixture(scope="function", autouse=True)
async def truncate_tables(db_session: AsyncSession):
    """
    Truncate all critical tables AFTER each test to ensure clean state.
    
    This fixture runs automatically (autouse=True) after every test,
    ensuring IntegrityError is prevented when tests share the same session.
    """
    yield  # Run test first
    
    # Truncate tables in correct order (respect foreign keys)
    # Order matters: tables with FK references should be truncated after their parents
    truncate_order = [
        "audit_trails",                    # Depends on users, organizations
        "waste_movements",                  # FASE 5B: Depends on organizations
        "employer_transporter_links",      # Depends on employers, transporters, organizations
        "residues",                         # Depends on employers, transporters, organizations
        "memberships",                      # Depends on users, organizations
        "employers",                        # Depends on organizations
        "transporters",                     # Depends on organizations
        "users",                            # No dependencies
        "organizations",                   # No dependencies
    ]
    
    try:
        for table in truncate_order:
            await db_session.execute(
                f"DELETE FROM {table}"
            )
        await db_session.commit()
    except Exception:
        await db_session.rollback()
        # Tables might not exist yet (first test) - this is OK