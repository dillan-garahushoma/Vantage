from fastapi import APIRouter


router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/status")
async def providers_status():
    return {
        "module": "providers",
        "status": "scaffolded",
        "next": "Add provider verification, assignment, completion notes, and ratings.",
    }
