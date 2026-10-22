from fastapi import APIRouter

from app.analytics.api.health_brief import router as health_brief_router
from app.analytics.api.intelligence import router as intelligence_router
from app.analytics.api.living_score import router as living_score_router

router = APIRouter(prefix="/analytics", tags=["analytics"])
router.include_router(living_score_router)
router.include_router(health_brief_router)
router.include_router(intelligence_router)


@router.get("/status")
async def analytics_status():
    return {
        "module": "analytics",
        "status": "available",
        "capabilities": ["living_score", "maintenance_intelligence", "briefing_history"],
    }
