"""
Identity API router — auth and user profile endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.exceptions import AlreadyExistsError, InvalidCredentialsError
from app.db.session import get_db
from app.identity.api.dependencies import RequireRole, get_current_user
from app.identity.domain.entities import User
from app.identity.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.identity.schemas.user import UserResponse
from app.identity.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> User:
    """Register a new user account."""
    service = AuthService(session)
    try:
        user = await service.register(payload)
        await session.commit()
        return user
    except AlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate and receive a JWT access token."""
    service = AuthService(session)
    try:
        return await service.login(payload)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)


users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user's profile."""
    return current_user


@users_router.get("/admin-only")
async def get_admin_data(
    current_user: User = Depends(RequireRole([UserRole.HOA_ADMIN, UserRole.SUPER_ADMIN]))
):
    """Demonstration endpoint that requires admin privileges."""
    return {"message": "Welcome, Admin!", "user_role": current_user.role}
