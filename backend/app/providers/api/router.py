from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.common.pagination import Page, PaginationParams
from app.core.config import get_settings
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser, require_roles
from app.identity.models.user import User
from app.providers.schemas.review import PaginatedReviewsResponse, ReviewCreate, ReviewResponse
from app.providers.schemas.service_provider import (
    ServiceProviderCreate,
    ServiceProviderResponse,
    ServiceProviderUpdate,
)
from app.providers.services.review_service import ReviewService
from app.providers.services.service_provider_service import ServiceProviderService

AdminOnly = Annotated[User, require_roles(UserRole.hoa_admin.value)]
ResidentOnly = Annotated[User, require_roles(UserRole.resident.value)]


def create_router(enable_legacy_routes: bool | None = None) -> APIRouter:
    if enable_legacy_routes is None:
        enable_legacy_routes = get_settings().ENABLE_LEGACY_ROUTES

    router = APIRouter(prefix="/providers", tags=["providers"])

    @router.get("", response_model=Page[ServiceProviderResponse])
    async def list_providers(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: CurrentUser,
        pagination: Annotated[PaginationParams, Depends()],
        trade: Annotated[str | None, Query(max_length=50, description="e.g. plumber")] = None,
        verified: Annotated[bool | None, Query()] = None,
        emergency_available: Annotated[bool | None, Query()] = None,
    ) -> Page[ServiceProviderResponse]:
        return await ServiceProviderService(db).list_providers(
            actor=current_user,
            page=pagination.page,
            size=pagination.size,
            trade=trade,
            verified=verified,
            emergency_available=emergency_available,
        )

    @router.get("/{provider_id}", response_model=ServiceProviderResponse)
    async def get_provider(
        provider_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: CurrentUser,
    ) -> ServiceProviderResponse:
        return await ServiceProviderService(db).get_provider(provider_id, current_user)

    if enable_legacy_routes:
        @router.post("", response_model=ServiceProviderResponse, status_code=201)
        async def create_provider(
            payload: ServiceProviderCreate,
            db: Annotated[AsyncSession, Depends(get_db)],
            _admin: AdminOnly,
        ) -> ServiceProviderResponse:
            return await ServiceProviderService(db).create_provider(payload)

        @router.patch("/{provider_id}", response_model=ServiceProviderResponse)
        async def update_provider(
            provider_id: int,
            payload: ServiceProviderUpdate,
            db: Annotated[AsyncSession, Depends(get_db)],
            _admin: AdminOnly,
        ) -> ServiceProviderResponse:
            """Edit details or mark a provider as verified."""
            return await ServiceProviderService(db).update_provider(provider_id, payload)

        @router.get("/{provider_id}/reviews", response_model=PaginatedReviewsResponse)
        async def list_provider_reviews(
            provider_id: int,
            db: Annotated[AsyncSession, Depends(get_db)],
            _user: CurrentUser,
        ) -> PaginatedReviewsResponse:
            return await ReviewService(db).list_reviews(provider_id)

        @router.post(
            "/{provider_id}/reviews", response_model=ReviewResponse, status_code=201
        )
        async def create_provider_review(
            provider_id: int,
            payload: ReviewCreate,
            db: Annotated[AsyncSession, Depends(get_db)],
            current_user: ResidentOnly,
        ) -> ReviewResponse:
            """Residents rate a provider 1-5. One review per resident per provider."""
            return await ReviewService(db).create_review(provider_id, payload, current_user)
    else:
        @router.post("", include_in_schema=False)
        async def legacy_provider_creation_disabled() -> None:
            raise HTTPException(status_code=404, detail="Not found")

        @router.patch("/{provider_id}", include_in_schema=False)
        async def legacy_provider_update_disabled(provider_id: int) -> None:
            raise HTTPException(status_code=404, detail="Not found")

    return router


router = create_router()
