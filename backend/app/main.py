"""
VALORA API — application entry point.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

# 1. Initialize logging before doing anything else
configure_logging()
logger = logging.getLogger(__name__)

# 2. Load settings
settings = get_settings()

# 3. Create FastAPI application
app = FastAPI(
    title="VALORA API",
    description="Property Health Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 4. CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with your specific frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Mount all domain routers
app.include_router(api_router)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info(f"Starting VALORA API in '{settings.ENVIRONMENT}' mode.")


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}
