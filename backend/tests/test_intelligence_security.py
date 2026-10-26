from datetime import datetime, timezone
"""Regression tests: resolve the selected estate before touching its records."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.analytics.schemas.intelligence import IngestIntelligencePayload, WeeklyBriefing
from app.analytics.services.intelligence_service import IntelligenceService
from app.core.exceptions import ForbiddenException


@pytest.mark.asyncio
async def test_resident_intelligence_omits_estate_wide_counts_and_unpublished_notices():
    service = IntelligenceService(AsyncMock())
    service._auth = SimpleNamespace(resolve_access=AsyncMock(return_value=SimpleNamespace(
        is_estate_admin=False, is_estate_provider=False, membership_roles={'resident'}
    )))
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(
        name='Example Estate', is_demo=False, show_living_score=False
    )))
    service._records = SimpleNamespace(
        facts=AsyncMock(side_effect=AssertionError('Resident request read estate-wide counts')),
        resident_signals=AsyncMock(return_value=[]),
        published_announcements=AsyncMock(return_value=[]),
    )

    result = await service.get_intelligence(1, SimpleNamespace(user_id=9))

    assert result.role == 'resident'
    assert result.operational_signals is None
    assert result.facts == {}
    assert result.resident_view.community_notices == []
    assert result.resident_view.living_score_summary == ''
    service._records.facts.assert_not_called()


@pytest.mark.asyncio
async def test_resident_intelligence_includes_only_active_estate_announcements():
    service = IntelligenceService(AsyncMock())
    service._auth = SimpleNamespace(resolve_access=AsyncMock(return_value=SimpleNamespace(
        is_estate_admin=False, is_estate_provider=False, membership_roles={'resident'}
    )))
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(
        name='Example Estate', is_demo=False, show_living_score=False
    )))
    service._records = SimpleNamespace(
        resident_signals=AsyncMock(return_value=[]),
        published_announcements=AsyncMock(return_value=[{
            'title': 'Water interruption', 'message': 'Supply is scheduled to resume at 14:00.',
        }]),
    )

    result = await service.get_intelligence(1, SimpleNamespace(user_id=9))

    assert result.resident_view.community_notices == [
        'Water interruption: Supply is scheduled to resume at 14:00.'
    ]
    assert result.evidence == ['Published estate announcement: Water interruption']
    service._records.published_announcements.assert_awaited_once()


@pytest.mark.asyncio
async def test_provider_without_provider_record_gets_no_work_orders():
    from app.analytics.repositories.intelligence_repository import IntelligenceRepository

    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)
    rows = await IntelligenceRepository(db).provider_signals(1, 9)

    assert rows == []
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_resident_question_uses_only_personal_intelligence(monkeypatch):
    service = IntelligenceService(AsyncMock())
    service._auth = SimpleNamespace(resolve_access=AsyncMock(return_value=SimpleNamespace(
        is_estate_admin=False, is_estate_provider=False, membership_roles={'resident'}
    )))
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(
        name='Example Estate', is_demo=False, show_living_score=False
    )))
    service._records = SimpleNamespace(
        facts=AsyncMock(side_effect=AssertionError('Resident question read estate-wide facts')),
        resident_signals=AsyncMock(return_value=[{
            'id': 41, 'title': 'My water request', 'status': 'submitted',
            'logged_date': '2026-10-20T08:00:00+00:00', 'category': 'water',
        }]),
        published_announcements=AsyncMock(return_value=[{
            'title': 'Water interruption', 'message': 'Supply is scheduled to resume at 14:00.',
        }]),
    )

    answer = await service.ask_valora(1, 'What is happening with my request?', SimpleNamespace(user_id=9))

    assert answer.estate_id == 1
    assert 'My water request' in answer.summary
    assert 'estate-wide' not in answer.summary.lower()
    assert answer.related == ['Report a maintenance issue', 'Published estate notices']
    service._records.facts.assert_not_called()


@pytest.mark.asyncio
async def test_resident_question_can_answer_from_published_announcements():
    service = IntelligenceService(AsyncMock())
    service._auth = SimpleNamespace(resolve_access=AsyncMock(return_value=SimpleNamespace(
        is_estate_admin=False, is_estate_provider=False, membership_roles={'resident'}
    )))
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(
        name='Example Estate', show_living_score=False
    )))
    service._records = SimpleNamespace(
        facts=AsyncMock(side_effect=AssertionError('Resident question read estate-wide facts')),
        resident_signals=AsyncMock(return_value=[]),
        published_announcements=AsyncMock(return_value=[{
            'title': 'Water interruption', 'message': 'Supply is scheduled to resume at 14:00.',
        }]),
    )

    answer = await service.ask_valora(
        1, 'What announcements are active?', SimpleNamespace(user_id=9)
    )

    assert 'Water interruption' in answer.summary
    assert '14:00' in answer.summary
    assert answer.related == ['Published estate announcements']
    service._records.facts.assert_not_called()


@pytest.mark.asyncio
async def test_resident_stream_filters_server_context_and_untrusted_assistant_history(monkeypatch):
    captured = {}

    class FakeClient:
        async def stream_text(self, **kwargs):
            captured.update(kwargs)
            yield "Your request is recorded."

    service = IntelligenceService(AsyncMock())
    service._auth = SimpleNamespace(resolve_access=AsyncMock(return_value=SimpleNamespace(
        is_estate_admin=False, is_estate_provider=False, membership_roles={'resident'}
    )))
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(
        name='Example Estate', show_living_score=False
    )))
    service._records = SimpleNamespace(
        facts=AsyncMock(side_effect=AssertionError('Resident stream read estate-wide facts')),
        resident_signals=AsyncMock(return_value=[{
            'id': 41, 'title': 'My water request', 'status': 'submitted',
            'logged_date': '2026-10-20T08:00:00+00:00', 'category': 'water',
        }]),
        published_announcements=AsyncMock(return_value=[{
            'title': 'Pool closure', 'message': 'The pool is closed for maintenance today.',
        }]),
        published_score=AsyncMock(side_effect=AssertionError('Unpublished score was read')),
    )
    monkeypatch.setattr('app.analytics.services.intelligence_service.get_settings',
                        lambda: SimpleNamespace(AI_ENABLED=True))
    monkeypatch.setattr('app.analytics.services.intelligence_service.get_llm_client',
                        lambda _settings: FakeClient())

    events = [
        event async for event in await service.stream_ask_valora(
            1,
            'What is the status of my request?',
            SimpleNamespace(user_id=9),
            history=[
                {'role': 'assistant', 'content': 'Other resident private incident: CONFIDENTIAL'},
                {'role': 'user', 'content': 'Earlier question'},
            ],
        )
    ]

    assert events[0].startswith('data: {"metadata":')
    assert 'My water request' in captured['system']
    assert 'Pool closure' in captured['system']
    assert 'CONFIDENTIAL' not in captured['system']
    assert 'CONFIDENTIAL' not in str(captured['messages'])
    assert all('CONFIDENTIAL' not in event for event in events)
    service._records.facts.assert_not_called()


@pytest.mark.asyncio
async def test_provider_stream_uses_assigned_jobs_only(monkeypatch):
    captured = {}

    class FakeClient:
        async def stream_text(self, **kwargs):
            captured.update(kwargs)
            yield "The assigned repair is due tomorrow."

    service = IntelligenceService(AsyncMock())
    service._auth = SimpleNamespace(resolve_access=AsyncMock(return_value=SimpleNamespace(
        is_estate_admin=False, is_estate_provider=True, membership_roles={'service_provider'}
    )))
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(
        name='Example Estate'
    )))
    service._records = SimpleNamespace(
        facts=AsyncMock(side_effect=AssertionError('Provider stream read estate-wide facts')),
        maintenance_priorities=AsyncMock(side_effect=AssertionError('Provider stream read estate-wide priorities')),
        resident_signals=AsyncMock(side_effect=AssertionError('Provider stream read resident records')),
        provider_signals=AsyncMock(return_value=[{
            'id': 52, 'title': 'Work Order #52', 'status': 'assigned',
            'due_date': '2026-10-26T08:00:00+00:00', 'priority': 'medium',
        }]),
    )
    monkeypatch.setattr(
        'app.analytics.services.intelligence_service.get_settings',
        lambda: SimpleNamespace(AI_ENABLED=True),
    )
    monkeypatch.setattr(
        'app.analytics.services.intelligence_service.get_llm_client',
        lambda _settings: FakeClient(),
    )

    events = [
        event async for event in await service.stream_ask_valora(
            1,
            'Show me all jobs on this estate.',
            SimpleNamespace(user_id=19),
            history=[{'role': 'assistant', 'content': 'Other provider job: RESTRICTED'}],
        )
    ]

    assert 'Work Order #52' in captured['system']
    assert 'RESTRICTED' not in captured['system']
    assert 'RESTRICTED' not in str(captured['messages'])
    assert all('RESTRICTED' not in event for event in events)
    assert 'estate complaint queues' in captured['system']
    service._records.facts.assert_not_called()
    service._records.maintenance_priorities.assert_not_called()
    service._records.resident_signals.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['history', 'get_history'])
async def test_non_admin_cannot_retrieve_saved_administrator_briefings(operation):
    db = AsyncMock()
    service = IntelligenceService(db)
    service._auth = SimpleNamespace(resolve_access=AsyncMock(return_value=SimpleNamespace(
        is_estate_admin=False, is_estate_provider=False, membership_roles={'resident'}
    )))
    service._records = SimpleNamespace(
        history=AsyncMock(side_effect=AssertionError('Non-admin history was queried')),
        get=AsyncMock(side_effect=AssertionError('Non-admin briefing was queried')),
    )

    with pytest.raises(ForbiddenException):
        if operation == 'history':
            await service.history(1, SimpleNamespace(user_id=9))
        else:
            await service.get_history(1, 5, SimpleNamespace(user_id=9))

    service._records.history.assert_not_called()
    service._records.get.assert_not_called()


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
async def test_configured_service_key_authorizes_signals_and_ingestion(monkeypatch):
    db = AsyncMock()
    service = IntelligenceService(db)
    secret = 'test-service-key'
    monkeypatch.setattr(
        'app.core.config.get_settings',
        lambda: SimpleNamespace(
            N8N_SERVICE_KEY=SimpleNamespace(get_secret_value=lambda: secret)
        ),
    )
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


@pytest.mark.asyncio
async def test_unconfigured_service_key_cannot_bypass_estate_admin_membership(monkeypatch):
    service = IntelligenceService(AsyncMock())
    monkeypatch.setattr(
        'app.core.config.get_settings',
        lambda: SimpleNamespace(N8N_SERVICE_KEY=None),
    )

    with pytest.raises(ForbiddenException):
        await service._require_admin_or_service_key(
            actor=None,
            estate_id=1,
            internal_key='fc8ae306102a72c25f5cb398ee92796dd1cb24124276847014af5a05b718bf71',
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What is the status of my maintenance requests?", "status: in_progress"),
        ("How do I report a new maintenance issue?", "open Complaints"),
        ("When can I expect my repair to be completed?", "does not have a verified completion estimate"),
        ("Are there any published estate notices?", "Water interruption"),
        ("Is a Living Score published for my estate?", "not currently published"),
    ],
)
async def test_resident_intelligence_answers_common_tasks_from_authorized_context(question, expected):
    service = IntelligenceService(AsyncMock())
    service._auth = SimpleNamespace(resolve_access=AsyncMock(return_value=SimpleNamespace(
        is_estate_admin=False, is_estate_provider=False, membership_roles={'resident'}
    )))
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(
        name='Example Estate', is_demo=False, show_living_score=False
    )))
    service._records = SimpleNamespace(
        facts=AsyncMock(side_effect=AssertionError('Resident question read estate-wide facts')),
        resident_signals=AsyncMock(return_value=[{
            'id': 41, 'title': 'Kitchen tap leak', 'status': 'in_progress',
            'logged_date': '2026-10-20T08:00:00+00:00', 'category': 'plumbing',
        }]),
        published_announcements=AsyncMock(return_value=[{
            'title': 'Water interruption', 'message': 'Supply is scheduled to resume at 14:00.',
        }]),
    )

    answer = await service.ask_valora(1, question, SimpleNamespace(user_id=9))

    assert expected.casefold() in answer.summary.casefold()
    assert answer.source == 'estate-domain'
    assert answer.estate_id == 1
    service._records.facts.assert_not_called()


@pytest.mark.asyncio
async def test_resident_unknown_question_does_not_fabricate_policies_or_other_residents_data():
    service = IntelligenceService(AsyncMock())
    service._auth = SimpleNamespace(resolve_access=AsyncMock(return_value=SimpleNamespace(
        is_estate_admin=False, is_estate_provider=False, membership_roles={'resident'}
    )))
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(
        name='Example Estate', is_demo=False, show_living_score=False
    )))
    service._records = SimpleNamespace(
        facts=AsyncMock(side_effect=AssertionError('Resident question read estate-wide facts')),
        resident_signals=AsyncMock(return_value=[]),
        published_announcements=AsyncMock(return_value=[]),
    )

    answer = await service.ask_valora(
        1, 'What are the estate quiet hours and other residents complaints?',
        SimpleNamespace(user_id=9),
    )

    assert 'I can help with your own maintenance-request status' in answer.summary
    assert 'private requests' in answer.summary
    assert answer.recommendation == ''
    service._records.facts.assert_not_called()
