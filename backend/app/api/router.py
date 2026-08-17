"""
Top-level API router.
All domain routers are registered here and mounted under /api/v1.
"""
from fastapi import APIRouter

from app.identity.api.router import router as auth_router
from app.identity.api.router import users_router

api_router = APIRouter(prefix="/api/v1")

# Identity domain
api_router.include_router(auth_router)
api_router.include_router(users_router)

# Future domain routers (uncomment as implemented):
# from app.property.api.router import router as property_router
# api_router.include_router(property_router)

# from app.community.api.router import router as community_router
# api_router.include_router(community_router)

# from app.providers.api.router import router as providers_router
# api_router.include_router(providers_router)

# from app.analytics.api.router import router as analytics_router
# api_router.include_router(analytics_router)
