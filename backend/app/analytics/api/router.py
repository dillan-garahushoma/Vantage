from fastapi import APIRouter


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/status")
async def analytics_status():
    return {
        "module": "analytics",
        "status": "scaffolded",
        "next": "Implement the deterministic Living Score engine before advanced ML.",
    }
