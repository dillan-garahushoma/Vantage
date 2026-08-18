from fastapi import APIRouter, BackgroundTasks, HTTPException
from uuid import uuid4
from app.kimi import services as kimi_services
from app.kimi.schemas import KimiStartRequest, KimiStatusResponse, KimiConfig

router = APIRouter(prefix="/kimi", tags=["kimi"]) 

@router.post("/start")
async def start_kimi(request: KimiStartRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid4())
    kimi_services.init_run(run_id, request.dict())
    # schedule background work
    background_tasks.add_task(kimi_services.schedule_run, run_id)
    return {"run_id": run_id}

@router.get("/status/{run_id}")
async def status(run_id: str):
    status = kimi_services.get_status(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return status

@router.get("/logs/{run_id}")
async def get_logs(run_id: str):
    logs = kimi_services.get_logs(run_id)
    if logs is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"logs": logs}

# admin endpoints
@router.get("/config")
async def get_config():
    return kimi_services.get_config()

@router.post("/config")
async def set_config(cfg: KimiConfig):
    kimi_services.set_config(cfg.dict())
    return {"ok": True}
