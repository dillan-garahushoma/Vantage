"""
Database convenience helpers.

This module provides high-level helpers used by application startup/shutdown
(e.g., creating/dropping all tables in test environments). For production
schema changes, always use Alembic migrations.
"""
from app.db.session import Base, engine


async def create_all_tables() -> None:
    """Create all tables defined on Base.metadata (useful for testing only)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    """Drop all tables defined on Base.metadata (useful for testing only)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
