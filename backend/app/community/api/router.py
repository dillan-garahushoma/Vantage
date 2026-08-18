from fastapi import APIRouter


router = APIRouter(prefix="/community", tags=["community"])


@router.get("/status")
async def community_status():
    return {
        "module": "community",
        "status": "scaffolded",
        "next": "Build complaint lifecycle, work orders, and HOA announcements.",
    }
