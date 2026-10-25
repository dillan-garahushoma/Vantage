"""Real PostgreSQL management completion and privacy acceptance."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.identity.api.dependencies import get_current_user
from app.identity.models.estate_membership import EstateMembership
from app.identity.models.estate_membership_event import EstateMembershipEvent
from app.community.models.complaint import Complaint
from app.community.models.maintenance_work_order import MaintenanceworkOrder
from app.main import app
from tests.factories import build_two_estate_world

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_unit_transfer_and_revocation_preserve_history(db_session, async_client):
    w = await build_two_estate_world(db_session)
    estate = w.estate_a.estate_id
    member = (await db_session.execute(select(EstateMembership).where(
        EstateMembership.user_id == w.resident_a1.user_id,
        EstateMembership.estate_id == estate))).scalars().first()
    params = {'estate_id': estate}
    app.dependency_overrides[get_current_user] = lambda: w.hoa_admin_a
    url = f'/api/v1/memberships/{member.membership_id}/unit'
    foreign = await async_client.patch(url, params=params, json={'property_id': w.property_b1.unit_id})
    assert foreign.status_code == 404
    response = await async_client.patch(url, params=params, json={'property_id': w.property_a2.unit_id})
    assert response.status_code == 200
    await db_session.refresh(member)
    assert member.property_id == w.property_a2.unit_id
    events = (await db_session.execute(select(EstateMembershipEvent).where(
        EstateMembershipEvent.user_id == w.resident_a1.user_id))).scalars().all()
    assert [(e.event_type, e.property_id) for e in events][-2:] == [
        ('removed', w.property_a1.unit_id), ('joined', w.property_a2.unit_id)]
    edited = await async_client.patch(f'/api/v1/properties/{w.property_a2.unit_id}',
        params=params, json={'bedrooms': 2, 'size_m2': '85.00'})
    assert edited.status_code == 200 and edited.json()['bedrooms'] == 2
    assert (await async_client.delete(f'/api/v1/memberships/{member.membership_id}', params=params)).status_code == 204
    remaining = (await db_session.execute(select(EstateMembership).where(EstateMembership.user_id == w.resident_a1.user_id, EstateMembership.estate_id == estate))).scalars().all()
    for other in remaining:
        assert (await async_client.delete(f'/api/v1/memberships/{other.membership_id}', params=params)).status_code == 204
    app.dependency_overrides[get_current_user] = lambda: w.resident_a1
    assert (await async_client.get('/api/v1/properties', params=params)).status_code == 403


async def test_priorities_are_grounded_manager_only_and_history_is_immutable(db_session, async_client):
    w = await build_two_estate_world(db_session)
    now = datetime.now(timezone.utc)
    complaint = Complaint(estate_id=w.estate_a.estate_id, user_id=w.resident_a1.user_id,
        unit_id=w.property_a1.unit_id, category='plumbing', description='PRIVATE TENANT DETAILS', priority='urgent')
    db_session.add(complaint)
    await db_session.flush()
    job = MaintenanceworkOrder(estate_id=w.estate_a.estate_id, complaint_id=complaint.complaint_id,
        provider_id=w.provider_profile_a.provider_id, estimated_completion_date=now - timedelta(days=2), status='in_progress')
    db_session.add(job)
    await db_session.commit()
    params = {'estate_id': w.estate_a.estate_id}
    app.dependency_overrides[get_current_user] = lambda: w.hoa_admin_a
    url = '/api/v1/analytics/intelligence/briefing/generate'
    saved = await async_client.post(url, params=params)
    assert saved.status_code == 201
    output = saved.json()
    assert output['recommendations']
    assert any('overdue' in r['title'].lower() for r in output['recommendations'])
    assert all(r['savingsZar'] is None for r in output['recommendations'])
    assert 'PRIVATE TENANT DETAILS' not in saved.text
    assert any(str(job.work_order_id) in e['source'] for r in output['recommendations'] for e in r['evidence'])
    job.status = 'completed'
    await db_session.commit()
    assert (await async_client.get(f"/api/v1/analytics/intelligence/history/{output['briefing_id']}", params=params)).json() == output
    app.dependency_overrides[get_current_user] = lambda: w.resident_a1
    safe = await async_client.get(f"/api/v1/analytics/intelligence/history/{output['briefing_id']}", params=params)
    assert safe.status_code == 403
    assert 'recommendations' not in safe.json()
    assert 'PRIVATE TENANT DETAILS' not in safe.text


async def test_completed_job_cannot_be_edited_without_status(db_session, async_client):
    w = await build_two_estate_world(db_session)
    complaint = Complaint(estate_id=w.estate_a.estate_id, user_id=w.resident_a1.user_id,
        unit_id=w.property_a1.unit_id, category='plumbing', description='A completed repair', status='resolved')
    db_session.add(complaint)
    await db_session.flush()
    job = MaintenanceworkOrder(estate_id=w.estate_a.estate_id, complaint_id=complaint.complaint_id,
        provider_id=w.provider_profile_a.provider_id, status='completed', completion_notes='Original evidence')
    db_session.add(job)
    await db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: w.provider_user_a
    params = {'estate_id': w.estate_a.estate_id}
    response = await async_client.patch(f'/api/v1/work-orders/{job.work_order_id}',
        params=params, json={'completion_notes': 'Replacement'})
    assert response.status_code == 409
    app.dependency_overrides[get_current_user] = lambda: w.resident_a1
    reopened = await async_client.post(f'/api/v1/complaints/{complaint.complaint_id}/reopen',
        params=params, json={'note': 'The leak returned today'})
    assert reopened.status_code == 200 and reopened.json()['status'] == 'submitted'
    await db_session.refresh(job)
    assert job.status == 'completed' and job.completion_notes == 'Original evidence'
    app.dependency_overrides[get_current_user] = lambda: w.hoa_admin_a
    assert (await async_client.patch(f'/api/v1/complaints/{complaint.complaint_id}/status',
        params=params, json={'status': 'reviewed'})).status_code == 200
    second = await async_client.post('/api/v1/work-orders', params=params, json={
        'complaint_id': complaint.complaint_id, 'provider_id': w.provider_profile_a.provider_id})
    assert second.status_code == 201
    second_id = second.json()['id']
    app.dependency_overrides[get_current_user] = lambda: w.provider_user_a
    for status in ('in_progress', 'completed'):
        assert (await async_client.patch(f'/api/v1/work-orders/{second_id}', params=params,
            json={'status': status})).status_code == 200
    app.dependency_overrides[get_current_user] = lambda: w.resident_a1
    assert (await async_client.post(f'/api/v1/work-orders/{job.work_order_id}/rating',
        params=params, json={'rating': 5})).status_code == 409
    assert (await async_client.post(f'/api/v1/work-orders/{second_id}/rating',
        params=params, json={'rating': 5})).status_code == 200


async def test_notifications_are_recipient_and_estate_scoped(db_session, async_client):
    w = await build_two_estate_world(db_session)
    params = {'estate_id': w.estate_a.estate_id}
    app.dependency_overrides[get_current_user] = lambda: w.resident_a1
    created = await async_client.post('/api/v1/complaints', params=params, json={
        'unit_id': w.property_a1.unit_id, 'category': 'water', 'description': 'Leaking kitchen tap'})
    assert created.status_code == 201
    app.dependency_overrides[get_current_user] = lambda: w.hoa_admin_a
    notices = await async_client.get('/api/v1/notifications', params=params)
    assert notices.status_code == 200 and notices.json()['total'] == 1
    notice = notices.json()['items'][0]
    assert notice['resource_id'] == created.json()['id']
    app.dependency_overrides[get_current_user] = lambda: w.resident_a1
    assert (await async_client.post(f"/api/v1/notifications/{notice['id']}/read", params=params)).status_code == 404
    app.dependency_overrides[get_current_user] = lambda: w.hoa_admin_b
    assert (await async_client.get('/api/v1/notifications', params=params)).status_code == 403


async def test_notification_opt_out_and_provider_global_role_are_enforced(db_session, async_client):
    w = await build_two_estate_world(db_session)
    params = {'estate_id': w.estate_a.estate_id}
    app.dependency_overrides[get_current_user] = lambda: w.hoa_admin_a
    assert (await async_client.patch('/api/v1/auth/preferences',
        json={'maintenance_notifications': False})).status_code == 200
    app.dependency_overrides[get_current_user] = lambda: w.resident_a1
    complaint = await async_client.post('/api/v1/complaints', params=params, json={
        'unit_id': w.property_a1.unit_id, 'category': 'water', 'description': 'A fictional dripping tap'})
    assert complaint.status_code == 201
    app.dependency_overrides[get_current_user] = lambda: w.hoa_admin_a
    assert (await async_client.get('/api/v1/notifications', params=params)).json()['total'] == 0
    ident = complaint.json()['id']
    assert (await async_client.patch(f'/api/v1/complaints/{ident}/status',
        params=params, json={'status': 'reviewed'})).status_code == 200
    # A stale provider membership never substitutes for the real global role.
    w.provider_user_a.role = 'resident'
    await db_session.commit()
    denied = await async_client.post('/api/v1/work-orders', params=params, json={
        'complaint_id': ident, 'provider_id': w.provider_profile_a.provider_id})
    assert denied.status_code == 404
