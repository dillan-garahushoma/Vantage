"""
Auth service — registration and login business logic.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, InvalidCredentialsError
from app.core.security import create_access_token, hash_password, verify_password
from app.identity.domain.entities import User
from app.identity.repositories.user_repository import UserRepository
from app.identity.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    """Handles user registration and authentication."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)

    async def register(self, payload: RegisterRequest) -> User:
        """Create a new user account.

        Raises:
            AlreadyExistsError: if the email is already registered.
        """
        existing = await self._repo.get_by_email(payload.email)
        if existing:
            raise AlreadyExistsError("User")

        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        return await self._repo.create(user)

    async def login(self, payload: LoginRequest) -> TokenResponse:
        """Authenticate a user and return a JWT access token.

        Raises:
            InvalidCredentialsError: if email/password do not match.
        """
        user = await self._repo.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise InvalidCredentialsError()

        token = create_access_token(subject=str(user.id))
        return TokenResponse(access_token=token)
