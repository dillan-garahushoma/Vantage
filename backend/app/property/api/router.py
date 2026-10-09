"""Property domain router: properties, listings and sales."""
from fastapi import APIRouter

from app.core.config import get_settings
from app.property.api.listings import router as listings_router
from app.property.api.properties import router as properties_router
from app.property.api.sales import router as sales_router


def create_router(enable_legacy_routes: bool | None = None) -> APIRouter:
    if enable_legacy_routes is None:
        enable_legacy_routes = get_settings().ENABLE_LEGACY_ROUTES

    router = APIRouter()
    router.include_router(properties_router)
    if enable_legacy_routes:
        router.include_router(listings_router)
        router.include_router(sales_router)
    return router


router = create_router()
