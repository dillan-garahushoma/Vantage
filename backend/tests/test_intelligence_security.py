from datetime import datetime, timezone
"""Regression tests: resolve the selected estate before touching its records."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.analytics.schemas.intelligence import IngestIntelligencePayload, WeeklyBriefing
from app.analytics.services.intelligence_service import IntelligenceService
from app.core.exceptions import ForbiddenException


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['signals', 'ingest'])
async def test_global_admin_with_resident_membership_cannot_export_or_ingest(operation):
    db = AsyncMock()
    service = IntelligenceService(db)
    service._auth = SimpleNamespace(resolve_access=AsyncMock(return_value=SimpleNamespace(is_estate_admin=False)))
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(name='Estate')))
    service._db.execute.side_effect = AssertionError('Unauthorized estate records were queried')
    actor = SimpleNamespace(user_id=1, role='hoa_admin')
    payload = IngestIntelligencePayload(briefing=WeeklyBriefing(
        headline='Unsupported', body='Invented', window_label='Now', signals_reviewed=0,
        sources=0, avoidable_zar=0), recommendations=[])
    with pytest.raises(ForbiddenException):
        if operation == 'signals':
            await service.get_estate_signals(2, actor=actor)
        else:
            await service.ingest_intelligence(2, payload, actor=actor)
    db.execute.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_ask_does_not_invent_pump_failure_or_score_change():
    service = IntelligenceService(AsyncMock())
    service._auth = SimpleNamespace(resolve_access=AsyncMock(return_value=SimpleNamespace(is_estate_admin=True)))
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(name='Empty estate')))
    service._records = SimpleNamespace(facts=AsyncMock(return_value={
        'counts': {'open_complaints': 0, 'work_orders_in_flight': 0, 'unresolved_incidents': 0},
        'latest_score': None, 'previous_score': None,
    }))
    answer = await service.ask_valora(2, 'Why did our estate health score change?', SimpleNamespace(user_id=1))
    assert 'no stored' in answer.summary.lower()
    assert 'score moved because' not in answer.summary.lower()
    assert all('Pool Pump' not in item for item in answer.evidence)


@pytest.mark.asyncio
async def test_service_secret_authorizes_signals_and_ingestion():
    db = AsyncMock()
    service = IntelligenceService(db)
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(name='Silverleaf', is_demo=False)))
    service._records = SimpleNamespace(
        facts=AsyncMock(return_value={
            'counts': {'open_complaints': 2, 'work_orders_in_flight': 1, 'unresolved_incidents': 0},
            'latest_score': None, 'previous_score': None,
        }),
        recent_signals=AsyncMock(return_value=[]),
        add=AsyncMock(side_effect=lambda **kw: SimpleNamespace(
            briefing_id=1, estate_id=kw.get('estate_id', 1), created_by=kw.get('created_by'),
            template_version=kw.get('template_version', 'operational-v1'),
            data_origin=kw.get('data_origin', 'live'), facts=kw.get('facts', {}),
            output=kw.get('output', {}), created_at=datetime.now(timezone.utc),
        )),
    )
    secret = 'fc8ae306102a72c25f5cb398ee92796dd1cb24124276847014af5a05b718bf71'
    signals = await service.get_estate_signals(1, actor=None, internal_key=secret)
    assert signals.estate_name == 'Silverleaf'
    assert signals.counts.open_complaints == 2

    payload = IngestIntelligencePayload(
        briefing=WeeklyBriefing(
            headline='2 items require attention',
            body='Operational records show 2 complaints.',
            window_label='Current',
            signals_reviewed=3,
            sources=3,
            avoidable_zar=None,
        ),
        recommendations=[],
    )
    ok = await service.ingest_intelligence(1, payload, actor=None, internal_key=secret)
    assert ok is True
