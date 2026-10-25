"""Real PostgreSQL acceptance of capability, grounding and immutable history."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.analytics.models.intelligence_briefing import IntelligenceBriefing
from app.analytics.models.living_score_snapshot import LivingScoreSnapshot
from app.analytics.schemas.intelligence import IngestIntelligencePayload
from app.analytics.services.intelligence_service import IntelligenceService
from app.community.models.complaint import Complaint
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.identity.api.dependencies import get_current_user
from app.identity.models.estate_membership import EstateMembership
from app.main import app
from tests.factories import build_two_estate_world

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_all_entrypoints_enforce_selected_estate_capability(db_session):
    w = await build_two_estate_world(db_session)
    s = IntelligenceService(db_session)
    estate = w.estate_b.estate_id
    payload = IngestIntelligencePayload(briefing=(await s.get_intelligence(estate, w.hoa_admin_b)).briefing, recommendations=[])
    for actor in (w.cross_user, w.resident_b1, w.provider_user_b, w.hoa_admin_a,
                  SimpleNamespace(user_id=w.hoa_admin_b.user_id, role='resident')):
        for call in (
            lambda: s.get_estate_signals(estate, actor=actor, internal_key='ignored'),
            lambda: s.ingest_intelligence(estate, payload, actor=actor, internal_key='ignored'),
            lambda: s.generate(estate, actor),
        ):
            with pytest.raises(ForbiddenException):
                await call()
    with pytest.raises(ForbiddenException):
        await s.get_estate_signals(estate, internal_key='ignored')
    assert (await s.get_estate_signals(estate, actor=w.hoa_admin_b)).estate_id == estate
    assert (await db_session.scalar(select(func.count()).select_from(IntelligenceBriefing))) == 0
    # Safe aggregate reads retain legitimate member access, including a global
    # admin who is only a resident here. This never grants writes or raw export.
    for member in (w.cross_user, w.resident_b1, w.provider_user_b):
        assert (await s.get_intelligence(estate, member)).estate_id == estate
        assert (await s.ask_valora(estate, 'Show records', member)).estate_id == estate
        with pytest.raises(ForbiddenException):
            await s.history(estate, member)
    for read in (lambda: s.get_intelligence(estate, w.hoa_admin_a),
                 lambda: s.ask_valora(estate, 'Show records', w.hoa_admin_a),
                 lambda: s.history(estate, w.hoa_admin_a),
                 lambda: s.get_history(estate, 1, w.hoa_admin_a)):
        with pytest.raises(ForbiddenException):
            await read()


async def test_history_survives_fresh_session_preserves_facts_and_scopes_ids(db_session, test_db_sessionmaker):
    w = await build_two_estate_world(db_session)
    s = IntelligenceService(db_session)
    estate = w.estate_a.estate_id
    preview = await s.get_intelligence(estate, w.hoa_admin_a)
    assert preview.briefing_id is None
    assert (await s.history(estate, w.hoa_admin_a)).total == 0
    first = await s.generate(estate, w.hoa_admin_a)
    db_session.add(Complaint(estate_id=estate, user_id=w.resident_a1.user_id,
                             unit_id=w.property_a1.unit_id, category='other', description='PRIVATE RESIDENT TEXT'))
    await db_session.commit()
    second = await s.generate(estate, w.hoa_admin_a)
    assert first.briefing_id != second.briefing_id
    assert first.operational_signals.open_complaints == 0
    assert second.operational_signals.open_complaints == 1
    async with test_db_sessionmaker() as fresh:
        other = IntelligenceService(fresh)
        assert await other.get_history(estate, first.briefing_id, w.hoa_admin_a) == first
        assert await other.get_intelligence(estate, w.hoa_admin_a) == second
        page = await other.history(estate, w.hoa_admin_a, page=2, size=1)
        assert (page.total, page.pages, page.items) == (2, 2, [first])
        with pytest.raises(NotFoundException):
            await other.get_history(w.estate_b.estate_id, first.briefing_id, w.hoa_admin_b)
        with pytest.raises(ForbiddenException):
            await other.get_history(estate, first.briefing_id, w.hoa_admin_b)
        assert 'PRIVATE RESIDENT TEXT' not in page.model_dump_json()
    # Revoking membership applies even when the content is already stored.
    membership = (await db_session.execute(select(EstateMembership).where(
        EstateMembership.estate_id == estate, EstateMembership.user_id == w.hoa_admin_a.user_id))).scalars().first()
    await db_session.delete(membership)
    await db_session.commit()
    with pytest.raises(ForbiddenException):
        await s.get_history(estate, first.briefing_id, w.hoa_admin_a)


async def test_counts_exceed_first_page_and_ingestion_rejects_fabrication(db_session):
    w = await build_two_estate_world(db_session)
    estate = w.estate_a.estate_id
    for _ in range(105):
        db_session.add(Complaint(estate_id=estate, user_id=w.resident_a1.user_id,
            unit_id=w.property_a1.unit_id, category='other', description='PRIVATE TEXT'))
    db_session.add(Complaint(estate_id=w.estate_b.estate_id, user_id=w.resident_b1.user_id,
        unit_id=w.property_b1.unit_id, category='other', description='FOREIGN TEXT'))
    await db_session.commit()
    s = IntelligenceService(db_session)
    current = await s.get_intelligence(estate, w.hoa_admin_a)
    assert current.operational_signals.open_complaints == 105
    answer = await s.ask_valora(estate, 'Predict pump failure next month', w.hoa_admin_a)
    assert 'cannot establish' in answer.summary
    assert any('105 open' in ev for ev in answer.evidence)
    export = await s.get_estate_signals(estate, actor=w.hoa_admin_a)
    assert len(export.signals) == 50 and export.counts.open_complaints == 105
    assert 'PRIVATE TEXT' not in export.model_dump_json()
    bad = current.briefing.model_copy(update={'body': 'Pool Pump 02 will fail; save R42000'})
    with pytest.raises(BadRequestException):
        await s.ingest_intelligence(estate, IngestIntelligencePayload(briefing=bad, recommendations=[]), actor=w.hoa_admin_a)
    assert (await s.history(estate, w.hoa_admin_a)).total == 0
    assert await s.ingest_intelligence(estate, IngestIntelligencePayload(
        briefing=current.briefing, recommendations=[]), actor=w.hoa_admin_a)
    assert (await s.history(estate, w.hoa_admin_a)).total == 1


async def test_score_evidence_comparison_and_insufficient_latest(db_session):
    w = await build_two_estate_world(db_session)
    estate = w.estate_a.estate_id
    now = datetime.now(timezone.utc)
    for index, value in enumerate((70, 80, None)):
        db_session.add(LivingScoreSnapshot(estate_id=estate, engine_version='1.0.0',
            as_of=now + timedelta(days=index), window_start=now - timedelta(days=90),
            status='scored' if value is not None else 'insufficient_data',
            overall_score=value, measured_weight=1 if value is not None else 0, inputs={}, explanation={}))
        await db_session.commit()
        answer = await IntelligenceService(db_session).ask_valora(estate, 'Why did our health score change?', w.hoa_admin_a)
        if index == 1:
            assert '80' in answer.summary and '70' in answer.summary
            assert 'do not establish why' in answer.summary
            assert any('living_score_snapshots #' in ev for ev in answer.evidence)
        if index == 2:
            assert 'insufficient data' in answer.summary


async def test_http_generate_history_grounding_and_error_envelopes(db_session, async_client):
    w = await build_two_estate_world(db_session)
    base = '/api/v1/analytics/intelligence'
    params = {'estate_id': w.estate_a.estate_id}
    app.dependency_overrides[get_current_user] = lambda: w.hoa_admin_a
    try:
        response = await async_client.post(base + '/briefing/generate', params=params)
        assert response.status_code == 201
        saved = response.json()
        assert saved['source'] == 'stored_records'
        assert 'signalsReviewed' in saved['briefing']
        detail = await async_client.get(base + f"/history/{saved['briefing_id']}", params=params)
        assert detail.json() == saved
        assert (await async_client.get(base + '/history', params=params)).json()['total'] == 1
        assert (await async_client.get(base + '/history', params=params | {'size': 101})).status_code == 422
        app.dependency_overrides[get_current_user] = lambda: w.resident_a1
        assert (await async_client.get(base + '/history', params=params)).status_code == 403
        denied = await async_client.post(base + '/briefing/generate', params=params)
        assert denied.status_code == 403 and 'request_id' in denied.json()['detail']
        for bad_params in ({'estate_id': 2147483648}, params | {'size': 101}):
            assert (await async_client.get(base + '/history', params=bad_params)).status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
