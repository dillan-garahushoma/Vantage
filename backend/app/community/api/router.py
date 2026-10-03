"""Community domain router: complaints, work orders and announcements."""
from fastapi import APIRouter

from app.community.api.announcements import router as announcements_router
from app.community.api.complaints import router as complaints_router
from app.community.api.work_orders import router as work_orders_router

router = APIRouter()
router.include_router(complaints_router)
router.include_router(work_orders_router)
router.include_router(announcements_router)
