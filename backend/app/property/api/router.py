"""Property domain router: properties, listings, sales, estate profile and photos.

The public directory (`public_router`) is mounted here too, but note that it takes
**no authentication**: it is the only unauthenticated router in the API and it
lives in `app/property/api/public.py` with its own allow-list DTOs.
"""
from fastapi import APIRouter

from app.core.config import get_settings
from app.property.api.estates import router as estates_router
from app.property.api.investments import router as investments_router
from app.property.api.listings import router as listings_router
from app.property.api.market import router as market_router
from app.property.api.properties import router as properties_router
from app.property.api.public import router as public_router
from app.property.api.sales import router as sales_router


def create_router(enable_legacy_routes: bool | None = None) -> APIRouter:
    if enable_legacy_routes is None:
        enable_legacy_routes = get_settings().ENABLE_LEGACY_ROUTES

    router = APIRouter()
    router.include_router(properties_router)
    router.include_router(investments_router)
    router.include_router(market_router)
    router.include_router(estates_router)
    router.include_router(public_router)
    if enable_legacy_routes:
        router.include_router(listings_router)
        router.include_router(sales_router)
    return router


router = create_router()
