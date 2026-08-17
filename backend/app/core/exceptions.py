"""
Application-wide custom exception classes.
These are raised by service/domain layers and caught by the API layer.
"""


class VALORAException(Exception):
    """Base exception for all VALORA application errors."""

    def __init__(self, message: str = "An unexpected error occurred."):
        self.message = message
        super().__init__(self.message)


class NotFoundError(VALORAException):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str = "Resource", identifier: str | int | None = None):
        msg = f"{resource} not found."
        if identifier is not None:
            msg = f"{resource} with id '{identifier}' not found."
        super().__init__(msg)


class AlreadyExistsError(VALORAException):
    """Raised when attempting to create a resource that already exists."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} already exists.")


class PermissionDeniedError(VALORAException):
    """Raised when a user lacks permission to perform an action."""

    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(message)


class InvalidCredentialsError(VALORAException):
    """Raised when authentication credentials are invalid."""

    def __init__(self):
        super().__init__("Invalid email or password.")


class TokenExpiredError(VALORAException):
    """Raised when a JWT or other token has expired."""

    def __init__(self):
        super().__init__("Token has expired.")


class InvalidTokenError(VALORAException):
    """Raised when a JWT or other token is malformed or invalid."""

    def __init__(self):
        super().__init__("Invalid token.")


class ValidationError(VALORAException):
    """Raised when domain-level validation fails (beyond Pydantic schema validation)."""

    def __init__(self, message: str = "Validation failed."):
        super().__init__(message)
