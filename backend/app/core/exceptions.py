from fastapi import HTTPException, status


class CredentialsException(HTTPException):
    """Raised when authentication credentials are invalid or missing."""

    def __init__(self, detail: str = "Could not validate credentials.") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(HTTPException):
    """Raised when the authenticated user lacks the required role."""

    def __init__(self, detail: str = "Access forbidden.") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class BadRequestException(HTTPException):
    """Raised when a request is well-formed but cannot be accepted as sent."""

    def __init__(self, detail: str = "The request could not be accepted.") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class PayloadTooLargeException(HTTPException):
    """Raised when an upload exceeds the size the API will read."""

    def __init__(self, detail: str = "The uploaded file is too large.") -> None:
        super().__init__(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=detail)


class NotFoundException(HTTPException):
    """Raised when a requested resource does not exist."""

    def __init__(self, detail: str = "Resource not found.") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictException(HTTPException):
    """Raised when an operation conflicts with existing data."""

    def __init__(self, detail: str = "Conflict with existing resource.") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class RateLimitException(HTTPException):
    """Raised when a client exceeds an allowed request/attempt rate."""

    def __init__(self, detail: str = "Too many requests. Please try again later.") -> None:
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


class ServiceUnavailableException(HTTPException):
    """Raised when a required external service is unavailable."""

    def __init__(self, detail: str = "The service is temporarily unavailable.") -> None:
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
