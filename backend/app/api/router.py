from fastapi import APIRouter

from app.analytics.api.router import router as analytics_router
from app.community.api.router import router as community_router
from app.identity.api.router import router as identity_router
from app.property.api.router import router as property_router
from app.providers.api.router import router as providers_router
from app.kimi.api.router import router as kimi_router


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(identity_router)
api_router.include_router(property_router)
api_router.include_router(community_router)
api_router.include_router(providers_router)
api_router.include_router(analytics_router)
api_router.include_router(kimi_router)
