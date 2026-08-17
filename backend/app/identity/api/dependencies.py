"""
Identity API dependencies.
Provides the get_current_user FastAPI dependency for protected routes.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.exceptions import InvalidTokenError, TokenExpiredError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.identity.domain.entities import User
from app.identity.repositories.user_repository import UserRepository

import uuid

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Decode the JWT and return the authenticated User entity.
    Raises 401 if the token is missing, expired, or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id_str = decode_access_token(token)
        user_id = uuid.UUID(user_id_str)
    except (InvalidTokenError, TokenExpiredError, ValueError):
        raise credentials_exception

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


class RequireRole:
    """
    FastAPI dependency that enforces Role-Based Access Control (RBAC).
    
    Usage::
        @router.post("/announcements")
        async def create_announcement(
            user: User = Depends(RequireRole([UserRole.HOA_ADMIN, UserRole.SUPER_ADMIN]))
        ):
            ...
    """

    def __init__(self, allowed_roles: list[UserRole]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user
