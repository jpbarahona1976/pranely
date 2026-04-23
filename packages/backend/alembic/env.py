"""
Alembic environment configuration for PRANELY.

This module configures Alembic to work with:
- SQLAlchemy 2.0 (sync or async)
- PostgreSQL 16 via asyncpg OR SQLite for local testing
- Multi-tenant models from app.models

The target_metadata is populated from Base.metadata to enable
automatic migration generation based on model definitions.
"""
from logging.config import fileConfig
from pathlib import Path
from typing import Any

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection

# Import Base from models to get all table definitions
from app.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add project's root path to sys.path for imports
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

# Model's MetaData object
target_metadata = Base.metadata


def get_database_url() -> str:
    """Get database URL from config or environment."""
    # Try config first
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    
    # Fallback to environment
    try:
        from app.core.config import settings
        return settings.DATABASE_URL
    except Exception:
        pass
    
    # For commands that don't need DB (like heads/history), return empty
    return ""


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    
    if not url:
        raise ValueError("Database URL not configured. Set DATABASE_URL env var.")
    
    # For offline mode with SQLite, use different dialect options
    is_sqlite = "sqlite" in url
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=is_sqlite,  # SQLite compatibility for alembic batch mode
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations with connection."""
    # Check if SQLite
    is_sqlite = "sqlite" in str(connection.engine.url)
    
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=is_sqlite,  # SQLite compatibility
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_database_url()
    
    if not url:
        raise ValueError("Database URL not configured. Set DATABASE_URL env var.")
    
    is_async = "+asyncpg" in url
    is_sqlite = "sqlite" in url
    
    if is_async and not is_sqlite:
        # Async PostgreSQL mode
        import asyncio
        from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
        
        async def run_async_migrations():
            configuration = config.get_section(config.config_ini_section)
            # Use psycopg2 URL for sync connection
            sync_url = url.replace("+asyncpg", "psycopg2")
            
            connectable: AsyncEngine = create_async_engine(
                sync_url,
                poolclass=pool.NullPool,
                echo=False,
            )
            
            async with connectable.connect() as connection:
                await connection.run_sync(do_run_migrations)
            
            await connectable.dispose()
        
        asyncio.run(run_async_migrations())
    else:
        # Sync mode (PostgreSQL with psycopg2 or SQLite)
        from sqlalchemy import create_engine
        
        # Convert asyncpg to sync driver
        sync_url = url.replace("+asyncpg", "")
        
        configuration = config.get_section(config.config_ini_section)
        configuration["sqlalchemy.url"] = sync_url
        
        if is_sqlite:
            connectable = create_engine(
                url,
                poolclass=pool.NullPool,
            )
        else:
            connectable = create_engine(
                sync_url,
                poolclass=pool.NullPool,
            )
        
        with connectable.connect() as connection:
            do_run_migrations(connection)
        
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()