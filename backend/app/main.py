import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import get_settings
from app.core.error_handlers import (
    http_exception_handler,
    starlette_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging


# 1. Initialize logging before doing anything else
configure_logging()
logger = logging.getLogger(__name__)

# 2. Get environment settings
settings = get_settings()

app = FastAPI(
    title="VALORA API",
    description="Property Health Intelligence Platform",
    version="1.0.0"
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, starlette_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# add CORS middelware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting VALORA API in {settings.ENVIRONMENT} mode.")

# 7. root and health Endpoints - kai
@app.get("/")
def root():
    return {
        "message": "Welcome to VALORA API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}

app.include_router(api_router)
