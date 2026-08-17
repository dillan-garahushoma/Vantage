"""
SQLAlchemy async engine, session factory, declarative base, and
the get_db FastAPI dependency.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True in development if you want SQL logs
    future=True,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ---------------------------------------------------------------------------
# Declarative base
# All entity classes inherit from this Base.
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base for all ORM entities."""

    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncSession:  # type: ignore[return]
    """Yield an async database session and ensure it is closed after the request."""
    async with AsyncSessionLocal() as session:
        yield session
