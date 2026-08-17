"""
User repository — all database interactions for the User entity.
Repositories keep raw SQL/ORM logic out of service classes.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.entities import User


class UserRepository:
    """Data-access layer for User entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()  # flush to get DB-generated defaults (e.g. id, created_at)
        await self._session.refresh(user)
        return user

    async def save(self, user: User) -> User:
        """Persist changes to an existing user."""
        await self._session.flush()
        await self._session.refresh(user)
        return user
