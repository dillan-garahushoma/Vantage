"""Consistent HTTP error responses for VALORA's public API."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.ai.errors import AIUnavailableError

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    req_id = getattr(request.state, "request_id", None)
    if req_id:
        return req_id
    scope_state = request.scope.get("state", {})
    return scope_state.get("request_id", "unknown")


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
        400: "BAD_REQUEST",
        401: "UNAUTHENTICATED",
        403: "FORBIDDEN",
        404: "RESOURCE_NOT_FOUND",
        409: "CONFLICT",
        413: "PAYLOAD_TOO_LARGE",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
    }.get(status_code, "REQUEST_FAILED")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
    headers = dict(exc.headers) if exc.headers else {}
    headers["X-Request-ID"] = _request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(request=request, code=_code_for_status(exc.status_code), message=message),
        headers=headers,
    )


async def starlette_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    headers = dict(exc.headers) if exc.headers else {}
    headers["X-Request-ID"] = _request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(
            request=request,
            code=_code_for_status(exc.status_code),
            message=str(exc.detail),
        ),
        headers=headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    cleaned_errors = []
    for err in exc.errors():
        cleaned_errors.append(
            {
                "loc": err.get("loc"),
                "msg": str(err.get("msg", "")),
                "type": str(err.get("type", "")),
            }
        )
    return JSONResponse(
        status_code=422,
        content=_error_body(
            request=request,
            code="VALIDATION_ERROR",
            message="One or more fields are invalid.",
            details=jsonable_encoder(cleaned_errors),
        ),
        headers={"X-Request-ID": _request_id(request)},
    )


async def ai_unavailable_exception_handler(
    request: Request, exc: AIUnavailableError
) -> JSONResponse:
    """Map an optional-feature AI failure to a clean 503.

    AI is never load-bearing, so a disabled, refused, over-budget or failing AI
    layer must not look like a server bug. The body carries the closed reason
    code and nothing else - never a key, a prompt or a provider response.
    """
    req_id = _request_id(request)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=_error_body(
            request=request,
            code="AI_UNAVAILABLE",
            message="AI assist is unavailable for this request.",
            details={"reason": exc.reason},
        ),
        headers={"X-Request-ID": req_id},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = _request_id(request)
    logger.exception("Unhandled error request_id=%s", req_id, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(
            request=request,
            code="INTERNAL_ERROR",
            message="An unexpected server error occurred.",
        ),
        headers={"X-Request-ID": req_id},
    )
