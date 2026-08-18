"""Identity API router.

Provides:
  POST /api/v1/auth/register  — user registration
  POST /api/v1/auth/login     — user login + JWT issuance
  GET  /api/v1/auth/me        — authenticated user profile

These paths match the frontend API contract in FrontEnd/src/api/authApi.js.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser
from app.identity.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.identity.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["identity"])


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Register a new user and return a JWT."""
    return await AuthService(db).register(payload)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Authenticate and return a JWT."""
    return await AuthService(db).login(payload)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
