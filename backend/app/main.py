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


import re

REQUEST_ID_REGEX = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestIdMiddleware:
    """Pure ASGI middleware guaranteeing X-Request-ID on all responses including 500s."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw_id = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"x-request-id":
                raw_id = value.decode("latin1", errors="ignore")
                break

        if raw_id and REQUEST_ID_REGEX.match(raw_id):
            req_id = raw_id
        else:
            req_id = str(uuid4())

        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = req_id

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                replaced = False
                for i, (h_name, _) in enumerate(headers):
                    if h_name.lower() == b"x-request-id":
                        headers[i] = (b"x-request-id", req_id.encode("latin1"))
                        replaced = True
                        break
                if not replaced:
                    headers.append((b"x-request-id", req_id.encode("latin1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


app.add_middleware(RequestIdMiddleware)

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
