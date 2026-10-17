"""Join-code request and response contracts."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JoinCodeCreateRequest(BaseModel):
    """Rotate the estate's join code.

    ``expires_in_days`` is optional: an omitted value issues a code that does not
    expire until it is rotated. The estate is never part of the body - it is a
    query parameter, and the membership check is what proves access.
    """

    expires_in_days: int | None = Field(default=None, ge=1, le=365)

    model_config = ConfigDict(extra="forbid")


class JoinCodeResponse(BaseModel):
    """The active code, returned only from an authenticated request body/response.

    The code appears here and nowhere else: never in a path, a query string, a log
    line or an error message.
    """

    code: str
    estate_id: int
    created_at: datetime
    expires_at: datetime | None = None
