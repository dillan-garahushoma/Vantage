from types import SimpleNamespace
from unittest.mock import AsyncMock
from datetime import timedelta

import pytest
from sqlalchemy import select
from app.common.datetime_utils import utcnow
from app.core.exceptions import BadRequestException
from app.core.security import create_access_token
from app.identity.models.account_support import RecoveryGrant
from app.identity.schemas.account_support import RecoveryConfirm
from app.identity.services.account_support_service import AccountSupportService, recovery_limiter
from app.identity.api.dependencies import get_current_user
from app.main import app
from tests.factories import build_two_estate_world

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_recovery_is_single_use_expiring_and_revokes_existing_sessions(db_session, async_client):
    w = await build_two_estate_world(db_session)
    w.resident_a1.email = 'recovery-resident@example.com'
    await db_session.commit()
    recovery_limiter.reset_all()
    messages = []
    sender = SimpleNamespace(send=AsyncMock(side_effect=lambda message: messages.append(message)))
    service = AccountSupportService(db_session, sender=sender)
    original = create_access_token({'sub': str(w.resident_a1.user_id), 'version': 0})
    await service.request_recovery(w.resident_a1.email, requester='test')
    assert len(messages) == 1
    code = messages[0].body.splitlines()[1]
    grant = (await db_session.execute(select(RecoveryGrant))).scalar_one()
    assert grant.token_digest != code
    payload = RecoveryConfirm(token=code, password='Updated-fictional-test-pass')
    await service.confirm_recovery(payload)
    assert (await async_client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + original})).status_code == 401
    with pytest.raises(BadRequestException):
        await service.confirm_recovery(payload)
    await service.request_recovery(w.resident_a1.email, requester='test')
    expired = (await db_session.execute(select(RecoveryGrant).where(RecoveryGrant.used_at.is_(None)))).scalar_one()
    expired.expires_at = utcnow() - timedelta(minutes=1)
    await db_session.commit()
    with pytest.raises(BadRequestException):
        await service.confirm_recovery(RecoveryConfirm(token=messages[-1].body.splitlines()[1], password='Other-fictional-pass'))
    signed_in = await async_client.post('/api/v1/auth/login', json={
        'email': w.resident_a1.email, 'password': 'Updated-fictional-test-pass'})
    assert signed_in.status_code == 200


async def test_preferences_persist_and_provisioning_requires_operator(db_session, async_client):
    w = await build_two_estate_world(db_session)
    app.dependency_overrides[get_current_user] = lambda: w.resident_a1
    response = await async_client.patch('/api/v1/auth/preferences', json={'maintenance_notifications': False})
    assert response.status_code == 200
    assert not (await async_client.get('/api/v1/auth/preferences')).json()['maintenance_notifications']
    trusted = {'full_name': 'New Estate Manager', 'email': 'new-manager@example.com',
        'password': 'Synthetic-manager-pass', 'account_type': 'estate_admin',
        'estate': {'name': 'New Musgrave Court', 'suburb': 'Musgrave', 'city': 'Durban', 'province': 'KwaZulu-Natal'}}
    assert (await async_client.post('/api/v1/auth/register', json=trusted)).status_code == 422
    assert (await async_client.post('/api/v1/auth/provision', json=trusted)).status_code == 403
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(user_id=0, role='platform_admin')
    created = await async_client.post('/api/v1/auth/provision', json=trusted)
    assert created.status_code == 201 and created.json()['role'] == 'hoa_admin'
    assert 'access_token' not in created.json()
