"""Authentication application service — orchestrates registration and login use cases."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.validators import normalise_email
from app.core.exceptions import ConflictException, CredentialsException
from app.core.security import create_access_token, hash_password, verify_password
from app.identity.models.user import User
from app.identity.repositories.user_repository import UserRepository
from app.identity.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = UserRepository(db)

    async def register(self, payload: RegisterRequest) -> AuthResponse:
        email = normalise_email(payload.email)

        existing = await self._repo.get_by_email(email)
        if existing is not None:
            raise ConflictException("An account with this email already exists.")

        password_hash = hash_password(payload.password)
        user = await self._repo.create(
            full_name=payload.full_name,
            email=email,
            password_hash=password_hash,
            role=payload.role.value,
            phoneno=payload.phoneno,
            unit_no=payload.unit_no,
        )

        return self._build_auth_response(user)

    async def login(self, payload: LoginRequest) -> AuthResponse:
        email = normalise_email(payload.email)
        user = await self._repo.get_by_email(email)

        if user is None or not verify_password(payload.password, user.password_hash):
            raise CredentialsException("Invalid email or password.")

        return self._build_auth_response(user)

    async def get_current_user(self, user_id: int) -> UserResponse:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise CredentialsException("User not found.")
        return UserResponse.model_validate(user)

    @staticmethod
    def _build_auth_response(user: User) -> AuthResponse:
        token = create_access_token({"sub": str(user.user_id), "role": user.role})
        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
