"""Explicit operator provisioning for management journey test setup.

Public signup remains resident-only and is tested separately. These helpers act
as the operator, provision through the guarded API, then sign in normally.
"""
from types import SimpleNamespace
import httpx
from app.identity.api.dependencies import get_current_user
from app.main import app


async def signup_fixture(client, url, *, json, **kwargs):
    if json.get('account_type') not in ('estate_admin', 'service_provider'):
        return await client.post(url, json=json, **kwargs)
    previous = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(user_id=0, role='platform_admin')
    try:
        result = await client.post('/api/v1/auth/provision', json=json)
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = previous
    if result.status_code != 201:
        return result
    signed_in = await client.post('/api/v1/auth/login', json={
        'email': json['email'], 'password': json['password']})
    assert signed_in.status_code == 200
    return httpx.Response(201, json=signed_in.json(), request=result.request)
