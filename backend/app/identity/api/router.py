"""Identity API router.

Provides:
  POST /api/v1/auth/register  — user registration
  POST /api/v1/auth/login     — user login + JWT issuance
  GET  /api/v1/auth/me        — authenticated user profile
  GET  /api/v1/auth/estates   — the estates the caller may act inside

These paths match the frontend API contract in frontend/src/lib/api.ts.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser
from app.identity.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.identity.schemas.estate_access import EstateAccessListResponse, EstateAccessResponse
from app.identity.services.auth_service import AuthService
from app.identity.services.estate_authorization_service import EstateAuthorizationService

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
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Authenticate and return a JWT.

    Every attempt is recorded for security monitoring and a per-account
    failure window is enforced before credentials are verified.
    """
    client_ip = request.client.host if request.client else None
    return await AuthService(db).login(payload, ip_address=client_ip)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.get("/estates", response_model=EstateAccessListResponse)
async def my_estates(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EstateAccessListResponse:
    """Return the estates this user has a persisted membership in.

    The estate is the tenant boundary, so the frontend must let the user pick
    from this server-resolved list rather than typing an ``estate_id``. An empty
    list means the user is registered but not yet provisioned by an HOA.
    """
    summaries = await EstateAuthorizationService(db).list_accessible_estates(current_user)
    return EstateAccessListResponse(
        estates=[
            EstateAccessResponse(
                estate_id=s.estate_id,
                estate_name=s.estate_name,
                suburb=s.suburb,
                city=s.city,
                province=s.province,
                membership_roles=sorted(s.membership_roles),
                property_ids=sorted(s.property_ids),
                is_estate_admin=s.is_estate_admin,
                is_estate_provider=s.is_estate_provider,
                is_demo=s.is_demo,
            )
            for s in summaries
        ]
    )
