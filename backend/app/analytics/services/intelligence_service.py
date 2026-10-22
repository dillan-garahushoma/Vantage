"""Grounded operational intelligence: stored facts, estate capability, no cache."""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.repositories.intelligence_repository import IntelligenceRepository
from app.analytics.schemas.intelligence import (
    AskValoraResponse, EstateIntelligenceResponse, EstateSignalsExport,
    IngestIntelligencePayload, OperationalSignalCounts, WeeklyBriefing,
    PriorityRecommendation, RecommendationEvidence, WorkOrderDefaults,
)
from app.common.pagination import Page
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.repositories.estate_repository import EstateRepository

VERSION = 'maintenance-v2'
LIMITATIONS = [
    'Counts describe current stored records, not a weekly activity total.',
    'No telemetry, failure prediction, verified savings or valuation evidence is available in this briefing.',
    'Score differences alone do not establish a cause; no score is recalculated on read.',
]


def _evidence(estate_id: int, facts: dict) -> list[str]:
    counts = facts['counts']
    evidence = [
        f"complaints [estate_id={estate_id}; status=submitted/reviewed/assigned/in_progress]: {counts['open_complaints']} open.",
        f"maintenance_work_orders [estate_id={estate_id}; status=assigned/in_progress]: {counts['work_orders_in_flight']} in flight.",
        f"security_incidents [estate_id={estate_id}; status!=resolved]: {counts['unresolved_incidents']} unresolved.",
    ]
    for key in ('latest_score', 'previous_score'):
        score = facts[key]
        if score:
            evidence.append(f"living_score_snapshots #{score['snapshot_id']} [estate_id={estate_id}; "
                            f"as_of={score['as_of']}; engine={score['engine_version']}]: "
                            f"{score['overall_score'] if score['overall_score'] is not None else 'insufficient data'} "
                            f"(status={score['status']}).")
    return evidence


def _briefing(estate_name: str, facts: dict) -> WeeklyBriefing:
    counts = facts['counts']
    return WeeklyBriefing(
        headline=f'Stored operational records for {estate_name}.',
        body=(f"There are {counts['open_complaints']} open complaints, "
              f"{counts['work_orders_in_flight']} work orders in flight and "
              f"{counts['unresolved_incidents']} unresolved security incidents. "
              'Review the source records before deciding on maintenance. Forecasts and savings are unavailable.'),
        window_label='Current stored records', signals_reviewed=sum(counts.values()),
        sources=3, avoidable_zar=None,
    )


class IntelligenceService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._auth = EstateAuthorizationService(db)
        self._estates = EstateRepository(db)
        self._records = IntelligenceRepository(db)

    async def _require_admin(self, actor: User | None, estate_id: int):
        if actor is None:
            raise ForbiddenException('An authenticated estate administrator is required.')
        access = await self._auth.resolve_access(actor, estate_id)
        if not access.is_estate_admin:
            raise ForbiddenException('Your estate membership does not permit this action.')

    async def _require_member(self, actor: User, estate_id: int):
        return await self._auth.resolve_access(actor, estate_id)

    async def _current(self, estate_id: int, *, include_priorities: bool = False) -> EstateIntelligenceResponse:
        estate = await self._estates.get_by_id(estate_id)
        if estate is None:
            raise NotFoundException('Estate not found.')
        facts = await self._records.facts(estate_id)
        now = datetime.now(timezone.utc)
        priorities = []
        if include_priorities:
            records = await self._records.maintenance_priorities(estate_id, now)
            facts['maintenance_priorities'] = records
            for record in records:
                overdue = record['kind'] == 'overdue_work_order'
                ident = record['id']
                title = f'Overdue work order #{ident}' if overdue else f"Unassigned {record['priority']} complaint #{ident}"
                source = f"maintenance_work_orders #{ident}" if overdue else f"complaints #{ident}"
                detail = (f"Expected completion: {record['due_at']}; status: {record['status']}"
                          if overdue else f"Recorded priority: {record['priority']}; created: {record['created_at']}")
                action = ('Review the existing work order and agree a revised completion date with the assigned provider.'
                          if overdue else 'Review this complaint, then select an authorized provider before creating a work order.')
                priorities.append(PriorityRecommendation(id=f"{record['kind']}-{ident}",
                    kind='EMERGING SERVICE RISK', title=title,
                    summary=detail, evidence=[RecommendationEvidence(label=source, detail=detail,
                        source=f'{source} [estate_id={estate_id}; measured_at={now.isoformat()}]')],
                    confidence='High', confidence_value=None, impact='Requires manager review; no financial estimate.',
                    savings_zar=None, suggested_action=action,
                    work_order_defaults=WorkOrderDefaults(title=title,
                        priority='high' if overdue else record['priority'], description=action)))
        return EstateIntelligenceResponse(
            estate_id=estate_id, estate_name=estate.name, as_of=now,
            briefing=_briefing(estate.name, facts), recommendations=priorities, template_version=VERSION,
            operational_signals=OperationalSignalCounts(**facts['counts']), source='stored_records',
            data_origin='demo' if bool(getattr(estate, 'is_demo', False)) else 'live',
            facts=facts, evidence=_evidence(estate_id, facts), limitations=LIMITATIONS,
        )

    @staticmethod
    def _for_viewer(output: EstateIntelligenceResponse, access) -> EstateIntelligenceResponse:
        if access.is_estate_admin:
            return output
        return output.model_copy(update={'recommendations': [],
            'facts': {key: value for key, value in output.facts.items() if key != 'maintenance_priorities'}})

    @staticmethod
    def _stored(row) -> EstateIntelligenceResponse:
        return EstateIntelligenceResponse.model_validate(row.output).model_copy(update={
            'briefing_id': row.briefing_id, 'as_of': row.created_at,
            'template_version': row.template_version, 'data_origin': row.data_origin,
        })

    async def get_intelligence(self, estate_id: int, actor: User) -> EstateIntelligenceResponse:
        access = await self._require_member(actor, estate_id)
        # Original measurement time stays with saved output; GET never writes.
        rows, _ = await self._records.history(estate_id, offset=0, limit=1)
        output = self._stored(rows[0]) if rows else await self._current(estate_id, include_priorities=access.is_estate_admin)
        return self._for_viewer(output, access)

    async def ask_valora(self, estate_id: int, question: str, actor: User) -> AskValoraResponse:
        access = await self._require_member(actor, estate_id)
        current = await self._current(estate_id, include_priorities=access.is_estate_admin and any(
            word in question.casefold() for word in ('priority', 'priorities', 'overdue', 'maintenance')))
        facts = current.facts
        q = question.casefold()
        summary = current.briefing.body
        if 'score' in q or 'health' in q:
            latest, previous = facts['latest_score'], facts['previous_score']
            if latest is None:
                summary = 'No stored Living Score snapshot is available for this estate.'
            elif latest['overall_score'] is None:
                summary = 'The latest stored Living Score has insufficient data; no numeric score is available.'
            elif previous and previous['overall_score'] is not None and previous['engine_version'] == latest['engine_version']:
                summary = (f"The stored score is {latest['overall_score']}/100; the preceding stored score was "
                           f"{previous['overall_score']}/100. These measurements do not establish why it changed.")
            else:
                summary = f"The stored score is {latest['overall_score']}/100. No comparable preceding numeric snapshot is available."
        elif any(word in q for word in ('next month', 'predict', 'failure', 'saving', 'roi', 'yield', 'price')):
            summary = 'Stored operational records cannot establish this forecast, saving or property return. ' + summary
        elif current.recommendations:
            summary = ' '.join(item.title + ': ' + item.summary for item in current.recommendations[:5])
        else:
            summary = 'I can summarize counts and stored Living Scores; asset-specific causes require additional evidence. ' + summary
        return AskValoraResponse(
            summary=summary, evidence=current.evidence + [ev.source for item in current.recommendations for ev in item.evidence],
            recommendation='Review the cited records; an estate administrator must verify any proposed action.',
            related=['Complaints', 'Work orders', 'Security incidents'], source='estate-domain',
            as_of=current.as_of, estate_id=estate_id, limitations=current.limitations,
        )

    async def get_estate_signals(self, estate_id: int, actor: User | None = None,
                                 internal_key: str | None = None) -> EstateSignalsExport:
        # Legacy header is not authority; integrations need an estate principal.
        await self._require_admin(actor, estate_id)
        current = await self._current(estate_id)
        return EstateSignalsExport(
            estate_id=estate_id, estate_name=current.estate_name, generated_at=current.as_of,
            counts=current.operational_signals, signals=await self._records.recent_signals(estate_id),
        )

    async def _save(self, current: EstateIntelligenceResponse, actor: User) -> EstateIntelligenceResponse:
        row = await self._records.add(
            estate_id=current.estate_id, created_by=actor.user_id, template_version=VERSION,
            data_origin=current.data_origin, facts=current.facts,
            output=current.model_dump(mode='json', by_alias=False), created_at=current.as_of,
        )
        await self._db.commit()
        return self._stored(row)

    async def generate(self, estate_id: int, actor: User) -> EstateIntelligenceResponse:
        await self._require_admin(actor, estate_id)
        return await self._save(await self._current(estate_id, include_priorities=True), actor)

    async def ingest_intelligence(self, estate_id: int, payload: IngestIntelligencePayload,
                                  actor: User | None = None, internal_key: str | None = None) -> bool:
        await self._require_admin(actor, estate_id)
        current = await self._current(estate_id)
        # JSON shape is not proof of grounding. Accept only the exact supported
        # projection. Free-text claims need a separately approved safe contract.
        if payload.briefing != current.briefing or payload.recommendations:
            raise BadRequestException('Unsupported intelligence claims. Generate a briefing from stored records instead.')
        await self._save(current, actor)
        return True

    async def history(self, estate_id: int, actor: User, *, page: int = 1, size: int = 20) -> Page[EstateIntelligenceResponse]:
        access = await self._require_member(actor, estate_id)
        rows, total = await self._records.history(estate_id, offset=(page - 1) * size, limit=size)
        return Page(items=[self._for_viewer(self._stored(row), access) for row in rows], total=total, page=page, size=size)

    async def get_history(self, estate_id: int, briefing_id: int, actor: User) -> EstateIntelligenceResponse:
        access = await self._require_member(actor, estate_id)
        row = await self._records.get(estate_id, briefing_id)
        if row is None:
            raise NotFoundException('Intelligence briefing not found.')
        return self._for_viewer(self._stored(row), access)
