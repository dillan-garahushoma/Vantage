"""Identity API dependencies — reusable FastAPI dependency injection for auth and RBAC."""
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CredentialsException, ForbiddenException
from app.core.security import decode_access_token
from app.db.session import get_db
from app.identity.models.user import User
from app.identity.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Decode JWT and return the authenticated user ORM object."""
    try:
        payload = decode_access_token(token)
        if "exp" not in payload:
            raise CredentialsException()
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            raise CredentialsException()
        if not isinstance(user_id_raw, (str, int)):
            raise CredentialsException()
        if isinstance(user_id_raw, str) and not user_id_raw.isdigit():
            raise CredentialsException()
        user_id = int(user_id_raw)
    except (JWTError, TypeError, ValueError, CredentialsException):
        raise CredentialsException()

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise CredentialsException()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user_optional(
    token: Annotated[str | None, Depends(oauth2_scheme_optional)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except Exception:
        return None


def require_roles(*roles: str):
    """Factory that returns a dependency enforcing one of the given roles."""

    async def _check(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise ForbiddenException(
                f"This action requires one of the following roles: {', '.join(roles)}."
            )
        return current_user

    return Depends(_check)
