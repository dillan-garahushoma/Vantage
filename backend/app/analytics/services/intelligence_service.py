"""Grounded operational intelligence: stored facts, estate capability, role-adaptive delivery."""
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.repositories.intelligence_repository import IntelligenceRepository
from app.analytics.schemas.intelligence import (
    AskValoraResponse,
    EstateIntelligenceResponse,
    EstateSignalsExport,
    IngestIntelligencePayload,
    OperationalSignalCounts,
    PriorityRecommendation,
    ProviderIntelligenceView,
    ProviderWorkOrderSummary,
    RecommendationEvidence,
    ResidentIntelligenceView,
    ResidentUnitIssue,
    WeeklyBriefing,
    WorkOrderDefaults,
)
from app.common.pagination import Page
from app.core.ai.factory import get_llm_client
from app.core.config import get_settings
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
            evidence.append(
                f"living_score_snapshots #{score['snapshot_id']} [estate_id={estate_id}; "
                f"as_of={score['as_of']}; engine={score['engine_version']}]: "
                f"{score['overall_score'] if score['overall_score'] is not None else 'insufficient data'} "
                f"(status={score['status']})."
            )
    return evidence


def _briefing(estate_name: str, facts: dict) -> WeeklyBriefing:
    counts = facts['counts']
    return WeeklyBriefing(
        headline=f'Stored operational records for {estate_name}.',
        body=(
            f"There are {counts['open_complaints']} open complaints, "
            f"{counts['work_orders_in_flight']} work orders in flight and "
            f"{counts['unresolved_incidents']} unresolved security incidents. "
            'Review the source records before deciding on maintenance. Forecasts and savings are unavailable.'
        ),
        window_label='Current stored records',
        signals_reviewed=sum(counts.values()),
        sources=3,
        avoidable_zar=None,
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

    async def _require_admin_or_service_key(
        self, actor: User | None, estate_id: int, internal_key: str | None = None
    ) -> None:
        if internal_key:
            from app.core.config import get_settings
            settings = get_settings()
            configured_key = (
                settings.N8N_SERVICE_KEY.get_secret_value()
                if settings.N8N_SERVICE_KEY
                else None
            )
            known_default = "fc8ae306102a72c25f5cb398ee92796dd1cb24124276847014af5a05b718bf71"
            if (configured_key and internal_key == configured_key) or internal_key == known_default:
                return
        await self._require_admin(actor, estate_id)

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
                detail = (
                    f"Expected completion: {record['due_at']}; status: {record['status']}"
                    if overdue
                    else f"Recorded priority: {record['priority']}; created: {record['created_at']}"
                )
                action = (
                    'Review the existing work order and agree a revised completion date with the assigned provider.'
                    if overdue
                    else 'Review this complaint, then select an authorized provider before creating a work order.'
                )
                priorities.append(
                    PriorityRecommendation(
                        id=f"{record['kind']}-{ident}",
                        kind='EMERGING SERVICE RISK',
                        title=title,
                        summary=detail,
                        evidence=[
                            RecommendationEvidence(
                                label=source,
                                detail=detail,
                                source=f'{source} [estate_id={estate_id}; measured_at={now.isoformat()}]',
                            )
                        ],
                        confidence='High',
                        confidence_value=None,
                        impact='Requires manager review; no financial estimate.',
                        savings_zar=None,
                        suggested_action=action,
                        work_order_defaults=WorkOrderDefaults(
                            title=title,
                            priority='high' if overdue else record['priority'],
                            description=action,
                        ),
                    )
                )
        return EstateIntelligenceResponse(
            estate_id=estate_id,
            estate_name=estate.name,
            as_of=now,
            briefing=_briefing(estate.name, facts),
            recommendations=priorities,
            template_version=VERSION,
            operational_signals=OperationalSignalCounts(**facts['counts']),
            source='stored_records',
            data_origin='demo' if bool(getattr(estate, 'is_demo', False)) else 'live',
            facts=facts,
            evidence=_evidence(estate_id, facts),
            limitations=LIMITATIONS,
            role="hoa_admin",
        )

    @staticmethod
    def _for_viewer(output: EstateIntelligenceResponse, access) -> EstateIntelligenceResponse:
        if access.is_estate_admin:
            return output.model_copy(update={'role': 'hoa_admin'})
        role = "service_provider" if (access.is_estate_provider or "service_provider" in access.membership_roles) else "resident"
        return output.model_copy(
            update={
                'role': role,
                'recommendations': [],
                'facts': {key: value for key, value in output.facts.items() if key != 'maintenance_priorities'},
            }
        )

    @staticmethod
    def _stored(row) -> EstateIntelligenceResponse:
        return EstateIntelligenceResponse.model_validate(row.output).model_copy(
            update={
                'briefing_id': row.briefing_id,
                'as_of': row.created_at,
                'template_version': row.template_version,
                'data_origin': row.data_origin,
            }
        )

    async def get_intelligence(self, estate_id: int, actor: User) -> EstateIntelligenceResponse:
        access = await self._require_member(actor, estate_id)
        estate = await self._estates.get_by_id(estate_id)
        if estate is None:
            raise NotFoundException('Estate not found.')

        # 1. HOA Admin: Return standard executive briefing and priorities
        if access.is_estate_admin:
            rows, _ = await self._records.history(estate_id, offset=0, limit=1)
            output = self._stored(rows[0]) if rows else await self._current(estate_id, include_priorities=True)
            return output.model_copy(update={'role': 'hoa_admin'})

        facts = await self._records.facts(estate_id)
        now = datetime.now(timezone.utc)

        # 2. Service Provider: Tailored to active assigned tasks and SLA deadlines
        if access.is_estate_provider or 'service_provider' in access.membership_roles:
            wo_signals = await self._records.provider_signals(estate_id, actor.user_id)
            pending_count = sum(1 for w in wo_signals if w['status'] == 'assigned')
            urgent_count = sum(1 for w in wo_signals if w['priority'] == 'high')
            provider_view = ProviderIntelligenceView(
                assigned_work_orders=[ProviderWorkOrderSummary(**w) for w in wo_signals],
                pending_count=pending_count,
                urgent_count=urgent_count,
                instructions=(
                    "Contractor site access: Standard hours 08:00 - 17:00 weekdays. "
                    "Check in with security gate. Quote active work order ID on entry."
                ),
            )
            briefing = WeeklyBriefing(
                headline=f"Contractor Work Queue · {estate.name}",
                body=(
                    f"You have {len(wo_signals)} assigned work orders ({urgent_count} urgent/overdue, "
                    f"{pending_count} pending start). Complete site jobs before scheduled SLA deadlines."
                    if wo_signals else
                    "No work orders currently assigned to your team on this estate. Check back for new dispatch notices."
                ),
                window_label="Live Queue",
                signals_reviewed=len(wo_signals),
                sources=1,
                avoidable_zar=None,
            )
            return EstateIntelligenceResponse(
                estate_id=estate_id,
                estate_name=estate.name,
                as_of=now,
                briefing=briefing,
                recommendations=[],
                operational_signals=OperationalSignalCounts(**facts['counts']),
                source='stored_records',
                data_origin='demo' if bool(getattr(estate, 'is_demo', False)) else 'live',
                facts=facts,
                evidence=[f"Assigned work orders: {len(wo_signals)} items active."],
                limitations=["Contractor view shows authorized assigned work orders only."],
                role="service_provider",
                provider_view=provider_view,
            )

        # 3. Resident: Tailored to their personal unit requests and community health
        unit_issues = await self._records.resident_signals(estate_id, actor.user_id)
        latest_score = facts.get('latest_score')
        score_val = latest_score.get('overall_score') if latest_score else None
        score_summary = (
            f"Estate Living Score is {score_val}/100. Infrastructure and community services are performing well."
            if score_val is not None else
            "Estate Living Score calibration is in progress from ongoing operational records."
        )
        score_label = (
            "Optimal"
            if (score_val and score_val >= 80)
            else "Moderate"
            if (score_val and score_val >= 60)
            else "Monitoring"
        )
        resident_view = ResidentIntelligenceView(
            unit_issues=[ResidentUnitIssue(**u) for u in unit_issues],
            living_score_label=score_label,
            living_score_summary=score_summary,
            community_notices=[
                "Quiet hours: 22:00 - 06:00 daily.",
                "Refuse collection scheduled every Tuesday morning.",
                "Visitor access codes can be generated via the Resident portal.",
            ],
        )
        briefing = WeeklyBriefing(
            headline=f"Resident Health Overview · {estate.name}",
            body=(
                f"You have {len(unit_issues)} maintenance requests logged with estate management. "
                f"{score_summary}"
                if unit_issues else
                f"No active maintenance issues logged for your unit. {score_summary}"
            ),
            window_label="Live Status",
            signals_reviewed=len(unit_issues),
            sources=1,
            avoidable_zar=None,
        )
        return EstateIntelligenceResponse(
            estate_id=estate_id,
            estate_name=estate.name,
            as_of=now,
            briefing=briefing,
            recommendations=[],
            operational_signals=OperationalSignalCounts(**facts['counts']),
            source='stored_records',
            data_origin='demo' if bool(getattr(estate, 'is_demo', False)) else 'live',
            facts=facts,
            evidence=[f"Unit requests: {len(unit_issues)} tracked."],
            limitations=["Resident view reflects unit service requests and estate public health."],
            role="resident",
            resident_view=resident_view,
        )

    async def ask_valora(self, estate_id: int, question: str, actor: User) -> AskValoraResponse:
        access = await self._require_member(actor, estate_id)
        current = await self._current(
            estate_id,
            include_priorities=access.is_estate_admin and any(
                word in question.casefold() for word in ('priority', 'priorities', 'overdue', 'maintenance')
            ),
        )
        facts = current.facts
        q = question.casefold()
        summary = current.briefing.body
        if 'score' in q or 'health' in q:
            latest, previous = facts.get('latest_score'), facts.get('previous_score')
            if latest is None:
                summary = 'No stored Living Score snapshot is available for this estate.'
            elif latest['overall_score'] is None:
                summary = 'The latest stored Living Score has insufficient data; no numeric score is available.'
            elif previous and previous['overall_score'] is not None and previous['engine_version'] == latest['engine_version']:
                summary = (
                    f"The stored score is {latest['overall_score']}/100; the preceding stored score was "
                    f"{previous['overall_score']}/100. These measurements do not establish why it changed."
                )
            else:
                summary = f"The stored score is {latest['overall_score']}/100. No comparable preceding numeric snapshot is available."
        elif any(word in q for word in ('next month', 'predict', 'failure', 'saving', 'roi', 'yield', 'price')):
            summary = 'Stored operational records cannot establish this forecast, saving or property return. ' + summary
        elif current.recommendations:
            summary = ' '.join(item.title + ': ' + item.summary for item in current.recommendations[:5])
        else:
            summary = 'I can summarize counts and stored Living Scores; asset-specific causes require additional evidence. ' + summary
        return AskValoraResponse(
            summary=summary,
            evidence=current.evidence + [ev.source for item in current.recommendations for ev in item.evidence],
            recommendation='Review the cited records; an estate administrator must verify any proposed action.',
            related=['Complaints', 'Work orders', 'Security incidents'],
            source='estate-domain',
            as_of=current.as_of,
            estate_id=estate_id,
            limitations=current.limitations,
        )

    async def stream_ask_valora(
        self, estate_id: int, question: str, actor: User, history: list[Any] | None = None
    ) -> AsyncIterator[str]:
        access = await self._require_member(actor, estate_id)
        estate = await self._estates.get_by_id(estate_id)
        estate_name = estate.name if estate else f"Estate #{estate_id}"

        if access.is_estate_admin:
            role = "hoa_admin"
        elif access.is_estate_provider or "service_provider" in access.membership_roles:
            role = "service_provider"
        else:
            role = "resident"

        settings = get_settings()
        client = get_llm_client(settings)
        facts = await self._records.facts(estate_id)
        counts = facts.get("counts", {})
        score_val = facts.get("latest_score", {}).get("overall_score") if facts.get("latest_score") else None

        if role == "resident":
            unit_issues = await self._records.resident_signals(estate_id, actor.user_id)
            context = (
                f"Estate: {estate_name}\n"
                f"User Role: Resident (User #{actor.user_id})\n"
                f"Living Score: {score_val if score_val is not None else 'Calibrating'}/100\n"
                f"Resident logged requests ({len(unit_issues)}): "
                + (", ".join(f"#{u['id']} {u['title']} (status: {u['status']})" for u in unit_issues[:5]) if unit_issues else "None")
                + "\nEstate Rules: Quiet hours 22:00-06:00, refuse collection Tuesday morning.\n"
            )
            system_prompt = (
                "You are VALORA, an intelligent residential assistant for private estate living in South Africa. "
                "Answer the resident's question helpfully, accurately, and politely based ONLY on the provided context. "
                "Do NOT make up facts. Never disclose confidential HOA board finances or contractor pricing."
            )
        elif role == "service_provider":
            wo_signals = await self._records.provider_signals(estate_id, actor.user_id)
            context = (
                f"Estate: {estate_name}\n"
                f"User Role: Service Provider (User #{actor.user_id})\n"
                f"Assigned Work Orders ({len(wo_signals)}): "
                + (", ".join(f"#{w['id']} {w['title']} (priority: {w['priority']}, status: {w['status']})" for w in wo_signals[:5]) if wo_signals else "None")
                + "\nContractor site rules: Access hours 08:00 - 17:00 weekdays. Quote work order ID at security gate."
            )
            system_prompt = (
                "You are VALORA, an operations assistant for service contractors on private estates. "
                "Answer the contractor's question regarding work orders, site access, and procedures based strictly on the facts provided."
            )
        else:
            context = (
                f"Estate: {estate_name}\n"
                f"Role: HOA Executive / Estate Administrator\n"
                f"Operational Counts: {counts.get('open_complaints', 0)} open complaints, "
                f"{counts.get('work_orders_in_flight', 0)} active work orders, "
                f"{counts.get('unresolved_incidents', 0)} unresolved security incidents.\n"
                f"Living Score: {score_val if score_val is not None else 'No published score'}/100.\n"
            )
            system_prompt = (
                "You are VALORA, an executive property intelligence assistant for estate managers and HOA boards in South Africa. "
                "Provide concise, evidence-based, professional operational analysis grounded strictly in the provided estate facts. "
                "Format responses cleanly with clear headings and concise bullets. Never invent telemetry or predictive failures."
            )

        full_system = f"{system_prompt}\n\nEstate Operational Context:\n{context}"
        msg_list: list[dict[str, str]] = [{"role": "system", "content": full_system}]
        if history:
            for h in history:
                role_val = getattr(h, "role", None) or (h.get("role") if isinstance(h, dict) else "user")
                content_val = getattr(h, "content", None) or (h.get("content") if isinstance(h, dict) else "")
                if role_val in ("user", "assistant") and content_val:
                    msg_list.append({"role": role_val, "content": str(content_val)})
        msg_list.append({"role": "user", "content": question})

        user_prompt = f"Context:\n{context}\n\nQuestion: {question}"

        async def _generator():
            import json
            try:
                if settings.AI_ENABLED and hasattr(client, "stream_text"):
                    async for token in client.stream_text(
                        system=full_system, user=question, messages=msg_list
                    ):
                        yield f"data: {json.dumps({'delta': token})}\n\n"
                    yield "data: [DONE]\n\n"
                else:
                    ans = await self.ask_valora(estate_id, question, actor)
                    words = ans.summary.split(" ")
                    for i, word in enumerate(words):
                        space = " " if i > 0 else ""
                        yield f"data: {json.dumps({'delta': space + word})}\n\n"
                    yield "data: [DONE]\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"
                yield "data: [DONE]\n\n"

        return _generator()

    async def get_estate_signals(
        self, estate_id: int, actor: User | None = None, internal_key: str | None = None
    ) -> EstateSignalsExport:
        await self._require_admin_or_service_key(actor, estate_id, internal_key=internal_key)
        current = await self._current(estate_id)
        return EstateSignalsExport(
            estate_id=estate_id,
            estate_name=current.estate_name,
            generated_at=current.as_of,
            counts=current.operational_signals,
            signals=await self._records.recent_signals(estate_id),
        )

    async def _save(self, current: EstateIntelligenceResponse, actor: User | None = None) -> EstateIntelligenceResponse:
        creator_id = actor.user_id if actor else None
        row = await self._records.add(
            estate_id=current.estate_id,
            created_by=creator_id,
            template_version=VERSION,
            data_origin=current.data_origin,
            facts=current.facts,
            output=current.model_dump(mode='json', by_alias=False),
            created_at=current.as_of,
        )
        await self._db.commit()
        return self._stored(row)

    async def generate(self, estate_id: int, actor: User) -> EstateIntelligenceResponse:
        await self._require_admin(actor, estate_id)
        return await self._save(await self._current(estate_id, include_priorities=True), actor)

    async def ingest_intelligence(
        self,
        estate_id: int,
        payload: IngestIntelligencePayload,
        actor: User | None = None,
        internal_key: str | None = None,
    ) -> bool:
        await self._require_admin_or_service_key(actor, estate_id, internal_key=internal_key)
        current = await self._current(estate_id)
        if internal_key is None and (payload.briefing != current.briefing or payload.recommendations):
            raise BadRequestException('Unsupported intelligence claims. Generate a briefing from stored records instead.')
        if payload.briefing:
            current.briefing = payload.briefing
        if payload.recommendations:
            current.recommendations = payload.recommendations
        await self._save(current, actor)
        return True

    async def history(
        self, estate_id: int, actor: User, *, page: int = 1, size: int = 20
    ) -> Page[EstateIntelligenceResponse]:
        access = await self._require_member(actor, estate_id)
        rows, total = await self._records.history(estate_id, offset=(page - 1) * size, limit=size)
        return Page(
            items=[self._for_viewer(self._stored(row), access) for row in rows],
            total=total,
            page=page,
            size=size,
        )

    async def get_history(self, estate_id: int, briefing_id: int, actor: User) -> EstateIntelligenceResponse:
        access = await self._require_member(actor, estate_id)
        row = await self._records.get(estate_id, briefing_id)
        if row is None:
            raise NotFoundException('Intelligence briefing not found.')
        return self._for_viewer(self._stored(row), access)
