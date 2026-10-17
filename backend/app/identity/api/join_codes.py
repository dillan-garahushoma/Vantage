"""Join-code router.

Both endpoints are estate-scoped by ``?estate_id=`` and both require an
``hoa_admin`` who actually administers that estate; the service re-checks the
membership, so a client-supplied ``estate_id`` is never proof of access. The code
itself travels only in the response body - never in the path, never in a query
string, and never in a log line.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser
from app.identity.schemas.join_code import JoinCodeCreateRequest, JoinCodeResponse
from app.identity.services.estate_join_code_service import EstateJoinCodeService

router = APIRouter(prefix="/join-codes", tags=["identity"])


@router.get("/current", response_model=JoinCodeResponse)
async def current_join_code(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> JoinCodeResponse:
    """Return the estate's active join code, or 404 when there is none."""
    return await EstateJoinCodeService(db).get_current(current_user, estate_id=estate_id)


@router.post("", response_model=JoinCodeResponse, status_code=201)
async def rotate_join_code(
    payload: JoinCodeCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    estate_id: Annotated[int, Query(gt=0)],
) -> JoinCodeResponse:
    """Revoke the current code and issue a new one."""
    return await EstateJoinCodeService(db).rotate(
        current_user, estate_id=estate_id, expires_in_days=payload.expires_in_days
    )
