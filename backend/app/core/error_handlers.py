"""Consistent HTTP error responses for VALORA's public API."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _error_body(*, request: Request, code: str, message: str, details: Any = None) -> dict:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": _request_id(request),
    }
    if details is not None:
        error["details"] = details
    return {"detail": error}


def _code_for_status(status_code: int) -> str:
    return {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHENTICATED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "RESOURCE_NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
    }.get(status_code, "REQUEST_FAILED")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(request=request, code=_code_for_status(exc.status_code), message=message),
        headers=exc.headers,
    )


async def starlette_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(
            request=request,
            code=_code_for_status(exc.status_code),
            message=str(exc.detail),
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_error_body(
            request=request,
            code="VALIDATION_ERROR",
            message="One or more fields are invalid.",
            details=exc.errors(),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error request_id=%s", _request_id(request), exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(
            request=request,
            code="INTERNAL_ERROR",
            message="An unexpected server error occurred.",
        ),
    )
