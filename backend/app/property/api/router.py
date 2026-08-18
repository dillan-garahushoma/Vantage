from fastapi import APIRouter


router = APIRouter(prefix="/property", tags=["property"])


@router.get("/status")
async def property_status():
    return {
        "module": "property",
        "status": "scaffolded",
        "next": "Add estate, property/unit, and resident assignment APIs.",
    }
