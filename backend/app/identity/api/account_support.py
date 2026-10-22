from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.pagination import Page
from app.db.session import get_db
from app.identity.api.dependencies import CurrentUser
from app.identity.schemas.account_support import (
    MessageResponse, NotificationResponse, PreferenceResponse, RecoveryConfirm, RecoveryRequest,
)
from app.identity.services.account_support_service import AccountSupportService

router = APIRouter(tags=['account support'])
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get('/auth/preferences', response_model=PreferenceResponse)
async def preferences(db: Db, actor: CurrentUser):
    return await AccountSupportService(db).preferences(actor)


@router.patch('/auth/preferences', response_model=PreferenceResponse)
async def update_preferences(payload: PreferenceResponse, db: Db, actor: CurrentUser):
    return await AccountSupportService(db).update_preferences(actor, payload)


@router.post('/auth/recovery/request', response_model=MessageResponse, status_code=202)
async def request_recovery(payload: RecoveryRequest, request: Request, db: Db):
    await AccountSupportService(db).request_recovery(str(payload.email),
        requester=request.client.host if request.client else 'unknown')
    return MessageResponse(message='If the account is eligible and email is enabled, recovery instructions will be sent.')


@router.post('/auth/recovery/confirm', response_model=MessageResponse)
async def confirm_recovery(payload: RecoveryConfirm, db: Db):
    await AccountSupportService(db).confirm_recovery(payload)
    return MessageResponse(message='Password changed. Sign in again.')


@router.get('/notifications', response_model=Page[NotificationResponse])
async def notifications(db: Db, actor: CurrentUser, estate_id: Annotated[int, Query(gt=0)],
                        page: Annotated[int, Query(ge=1)] = 1,
                        size: Annotated[int, Query(ge=1, le=100)] = 20):
    return await AccountSupportService(db).notifications(actor, estate_id, page, size)


@router.post('/notifications/{notification_id}/read', response_model=NotificationResponse)
async def mark_read(notification_id: int, db: Db, actor: CurrentUser,
                    estate_id: Annotated[int, Query(gt=0)]):
    return await AccountSupportService(db).mark_read(actor, estate_id, notification_id)
