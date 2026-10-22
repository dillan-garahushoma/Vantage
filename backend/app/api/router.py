from fastapi import APIRouter

from app.analytics.api.router import router as analytics_router
from app.community.api.router import router as community_router
from app.contact.api.router import router as contact_router
from app.identity.api.join_codes import router as join_codes_router
from app.identity.api.memberships import router as memberships_router
from app.identity.api.residency_requests import router as residency_requests_router
from app.identity.api.router import router as identity_router
from app.identity.api.account_support import router as account_support_router
from app.core.config import get_settings
from app.property.api.router import create_router as create_property_router
from app.providers.api.router import create_router as create_providers_router


def create_api_router(enable_legacy_routes: bool | None = None) -> APIRouter:
    if enable_legacy_routes is None:
        enable_legacy_routes = get_settings().ENABLE_LEGACY_ROUTES

    router = APIRouter(prefix="/api/v1")
    router.include_router(identity_router)
    router.include_router(account_support_router)
    router.include_router(join_codes_router)
    router.include_router(memberships_router)
    router.include_router(residency_requests_router)
    router.include_router(create_property_router(enable_legacy_routes))
    router.include_router(community_router)
    router.include_router(create_providers_router(enable_legacy_routes))
    router.include_router(analytics_router)
    router.include_router(contact_router)
    return router


api_router = create_api_router()
