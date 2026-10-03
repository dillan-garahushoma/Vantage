"""Property domain router: properties, listings and sales."""
from fastapi import APIRouter

from app.property.api.listings import router as listings_router
from app.property.api.properties import router as properties_router
from app.property.api.sales import router as sales_router

router = APIRouter()
router.include_router(properties_router)
router.include_router(listings_router)
router.include_router(sales_router)
