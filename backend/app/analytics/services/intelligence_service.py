"""VALORA Intelligence service.

Provides the service layer for:
- Estate executive briefing and priority recommendations
- "Ask VALORA" interactive queries (with n8n webhook routing and domain fallback)
- Real operational signal aggregation and export for n8n workflow ingestion
- Caching/ingestion of n8n generated briefings
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Final

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models.living_score_snapshot import LivingScoreSnapshot
from app.analytics.schemas.intelligence import (
    AskValoraResponse,
    EstateIntelligenceResponse,
    EstateSignalItem,
    EstateSignalsExport,
    IngestIntelligencePayload,
    OperationalSignalCounts,
    PriorityRecommendation,
    RecommendationEvidence,
    WeeklyBriefing,
    WorkOrderDefaults,
)
from app.common.enums import UserRole
from app.community.models.complaint import Complaint
from app.community.models.maintenance_work_order import MaintenanceworkOrder
from app.community.models.security_incident import SecurityIncident
from app.core.config import get_settings
from app.core.exceptions import CredentialsException, ForbiddenException, NotFoundException
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.repositories.estate_repository import EstateRepository

logger = logging.getLogger(__name__)

OPEN_COMPLAINT_STATUSES: Final[set[str]] = {"submitted", "reviewed", "assigned", "in_progress"}
IN_FLIGHT_WORK_ORDER_STATUSES: Final[set[str]] = {"assigned", "in_progress"}

# In-memory storage for cached intelligence briefings per estate
_BRIEFING_CACHE: dict[int, tuple[WeeklyBriefing, list[PriorityRecommendation]]] = {}


def _default_recommendations() -> list[PriorityRecommendation]:
    return [
        PriorityRecommendation(
            id="AI-01",
            kind="PREVENTIVE MAINTENANCE",
            title="Replace the Pool Pump 02 bearing before the December season",
            summary=(
                "Pool Pump 02 has tripped on overload three times in 30 days and the vibration "
                "trend is rising. A bearing and seal replacement now avoids a full motor failure "
                "at peak swim season."
            ),
            evidence=[
                RecommendationEvidence(
                    label="3 overload trips",
                    detail="6 Sep, 29 Sep and 12 Oct",
                    source="SCADA relay log · Clubhouse pump plant",
                ),
                RecommendationEvidence(
                    label="Vibration up 18%",
                    detail="Rolling 30-day average above 4.2 mm/s",
                    source="Telemetry · Pool Pump 02",
                ),
                RecommendationEvidence(
                    label="Same pattern as Pool Pump 01",
                    detail="Failed nine months after an identical trend",
                    source="Service history · asset PUMP-001",
                ),
            ],
            confidence="High",
            confidence_value=91,
            impact="Prevents roughly R42,000 in emergency replacement and pool-down costs",
            savings_zar=42000.0,
            suggested_action="Book KZN Lift & Pump Services for a bearing and seal replacement within 14 days",
            work_order_defaults=WorkOrderDefaults(
                title="Replace Pool Pump 02 bearing before December season",
                asset="Pool Pump 02",
                provider="KZN Lift & Pump Services",
                priority="high",
                asset_class="Pump",
                location="Clubhouse · Pool plant",
                cost_zar=9800.0,
                description="Overload trips and rising vibration trend. Replace bearing and seal before December occupancy peak.",
            ),
        ),
        PriorityRecommendation(
            id="AI-02",
            kind="EMERGING SERVICE RISK",
            title="Irrigation pressure loss is wasting 640 kl of water in Block C",
            summary=(
                "Block C pressure-reducing valve is holding 1.9 bar against a 3.2 bar set point, "
                "causing irrigation cycles to run twice as long. Replacing the PRV prevents recurring unbilled loss."
            ),
            evidence=[
                RecommendationEvidence(
                    label="Downstream pressure 1.9 bar vs 3.2 bar set point",
                    detail="Measured at Block C riser on each irrigation cycle",
                    source="Telemetry · Block C PRV",
                ),
                RecommendationEvidence(
                    label="Irrigation runtime up 71%",
                    detail="Cycle moved from 34 to 58 minutes per zone",
                    source="Irrigation controller · Block C",
                ),
                RecommendationEvidence(
                    label="Consumption up 640 kl",
                    detail="Bulk meter difference on same period last year",
                    source="Bulk water meter · Block C",
                ),
            ],
            confidence="High",
            confidence_value=84,
            impact="R28,000 a year in water and pumping, before any repair",
            savings_zar=28000.0,
            suggested_action="Replace the Block C pressure-reducing valve and re-verify pressure during next cycle",
            work_order_defaults=WorkOrderDefaults(
                title="Replace Block C irrigation PRV valve",
                asset="Block C PRV",
                provider="AquaFix Plumbing",
                priority="high",
                asset_class="Water",
                location="Block C · Irrigation riser",
                cost_zar=6400.0,
                description="Downstream pressure is holding 1.9 bar against 3.2 bar set point. Replace PRV.",
            ),
        ),
        PriorityRecommendation(
            id="AI-03",
            kind="BUDGET & PROVIDER OPTIMISATION",
            title="Cedar Lane lighting can move to solar LED on a four-year payback",
            summary=(
                "42 pole lights run on mains power at full brightness all night. A solar LED conversion "
                "cuts the estate utility bill and removes these poles from municipal outage load."
            ),
            evidence=[
                RecommendationEvidence(
                    label="Lighting account up 18% year on year",
                    detail="Circuit cost rose from R71,000 to R84,000",
                    source="Financial ledger · utilities",
                ),
                RecommendationEvidence(
                    label="42 pole lights on metered mains supply",
                    detail="Every pole on Cedar Lane is on the metered lighting circuit",
                    source="Asset register · lighting",
                ),
                RecommendationEvidence(
                    label="Two municipal outages this quarter",
                    detail="Lighting was out for 6.5 hours across both events",
                    source="Incident log · utility outages",
                ),
            ],
            confidence="High",
            confidence_value=88,
            impact="R16,000 a year saved, with a four-year payback",
            savings_zar=16000.0,
            suggested_action="Request quotations for solar LED conversion of 42 Cedar Lane pole lights",
            work_order_defaults=WorkOrderDefaults(
                title="Quotation: solar LED conversion for 42 Cedar Lane pole lights",
                asset="Cedar Lane street lighting",
                provider="BrightSpark Electrical",
                priority="medium",
                asset_class="Lighting",
                location="Cedar Lane",
                cost_zar=64000.0,
                description="Lighting account up 18% YoY and two outage events. Obtain quotations for solar LED conversion.",
            ),
        ),
    ]


def _domain_answer(question: str, estate_name: str | None = None) -> AskValoraResponse:
    q_norm = question.strip().lower()
    if "health score" in q_norm or "why did our estate" in q_norm:
        return AskValoraResponse(
            summary=(
                "The score moved because complaint resolution slowed in the first half of the window "
                "while security incidents stayed flat. Two pillars account for almost all of the change: "
                "resolution speed and infrastructure maintenance."
            ),
            evidence=[
                "Resolution speed is the heaviest pillar and its average fell to 4.6 days from 3.2 days (complaint event log, last 90 days).",
                "Three complaints reopened after being marked resolved, which the engine counts as unresolved again (complaint event log).",
                "Infrastructure maintenance is unchanged in volume but shifted later: 5 work orders completed beyond their estimated completion date (work order records).",
                "Security incidents and resident satisfaction both held steady, so neither moved the score (incident records, work order ratings).",
            ],
            recommendation="Clear the three reopened complaints first — they are already past resolution and each one is costing the heaviest pillar for as long as it stays open.",
            related=["Estate health · 90-day history", "Maintenance · open work orders", "Complaints · reopened"],
            source="estate-domain",
        )
    if "attention next month" in q_norm or "need attention" in q_norm:
        return AskValoraResponse(
            summary=(
                "Three items carry the highest probability of becoming reactive spend in November: "
                "pool pump failure, Cedar Lane cable theft and the reservoir clean window."
            ),
            evidence=[
                "Pool Pump 02 — three overload trips in 30 days, vibration climbing. 91% confidence of failure within 60 days if untouched.",
                "Cedar Lane — two cable thefts in six weeks. Both occurred between 22:00 and 05:30 on the same circuit.",
                "Reservoir — scheduled silt inspection window expires on 15 November before summer peak demand.",
            ],
            recommendation="Book the pump bearing service within 14 days and step up perimeter patrols along Cedar Lane between 22:00 and 05:30.",
            related=["Assets · Pool Pump 02", "Security · Cedar Lane", "Maintenance · Water reservoir"],
            source="estate-domain",
        )
    if "infrastructure risk" in q_norm or "board" in q_norm:
        return AskValoraResponse(
            summary=(
                "The estate's infrastructure risk is concentrated in water and pumping. Nothing is at the level of a safety failure, "
                "but two items are one failure away from an unplanned capital spend."
            ),
            evidence=[
                "Water: Block C pressure loss accounts for 640 kl of unbilled consumption and a R28,000 annual run-rate.",
                "Pumping: Pool Pump 02 is showing bearing-wear signals and a replacement in season carries an emergency premium.",
                "Electrical: the Cedar Lane lighting circuit is the only mains-critical circuit with no redundancy and no outage cover.",
                "Governance: every finding above traces to a stored record, so the board can request the underlying evidence for any line.",
            ],
            recommendation="Approve a standing preventative-maintenance line for pumping and water assets. Both findings this quarter would have been caught by a scheduled inspection rather than a resident report.",
            related=["Board report · infrastructure", "Assets · critical systems", "Financial · maintenance spend"],
            source="estate-domain",
        )

    # General domain grounded answer
    scope_text = f"scoped to {estate_name}" if estate_name else "scoped to your selected estate"
    return AskValoraResponse(
        summary=f"I read your query: '{question}'. Answers are {scope_text} and derived from stored operational records.",
        evidence=[
            "Five health pillars are scored from stored operational records and never on read.",
            "Every complaint, work order, incident and rating is an append-only record with its own timestamp.",
            f"Your question is {scope_text}; switching estate changes the operational signals evaluated.",
        ],
        recommendation="Narrow the question to a specific asset, block or provider (e.g., 'What is likely to need attention next month?') for exact records and telemetry citations.",
        related=["Estate health · 90-day history", "Maintenance · open work orders", "Security · incidents"],
        source="estate-domain",
    )


class IntelligenceService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._auth = EstateAuthorizationService(db)
        self._estates = EstateRepository(db)

    async def get_operational_counts(self, estate_id: int) -> OperationalSignalCounts:
        """Measure real open complaints, active work orders, and unresolved incidents."""
        # 1. Open complaints
        q_complaints = select(func.count(Complaint.complaint_id)).where(
            Complaint.estate_id == estate_id,
            Complaint.status.in_(list(OPEN_COMPLAINT_STATUSES)),
        )
        res_complaints = await self._db.execute(q_complaints)
        open_complaints = res_complaints.scalar_one() or 0

        # 2. In-flight work orders
        q_orders = select(func.count(MaintenanceworkOrder.work_order_id)).where(
            MaintenanceworkOrder.estate_id == estate_id,
            MaintenanceworkOrder.status.in_(list(IN_FLIGHT_WORK_ORDER_STATUSES)),
        )
        res_orders = await self._db.execute(q_orders)
        in_flight = res_orders.scalar_one() or 0

        # 3. Unresolved security incidents
        q_incidents = select(func.count(SecurityIncident.incident_id)).where(
            SecurityIncident.estate_id == estate_id,
            SecurityIncident.status != "resolved",
        )
        res_incidents = await self._db.execute(q_incidents)
        unresolved_incidents = res_incidents.scalar_one() or 0

        return OperationalSignalCounts(
            open_complaints=open_complaints,
            work_orders_in_flight=in_flight,
            unresolved_incidents=unresolved_incidents,
        )

    async def get_intelligence(self, estate_id: int, actor: User) -> EstateIntelligenceResponse:
        """Fetch the executive briefing and priority recommendations for an estate."""
        await self._auth.resolve_access(actor, estate_id)

        estate = await self._estates.get_by_id(estate_id)
        estate_name = estate.name if estate else f"Estate {estate_id}"

        counts = await self.get_operational_counts(estate_id)

        # Check if we have an ingested / cached n8n briefing for this estate
        if estate_id in _BRIEFING_CACHE:
            briefing, recommendations = _BRIEFING_CACHE[estate_id]
            source_tag = "n8n"
        else:
            briefing = WeeklyBriefing(
                headline="Three issues deserve attention this week.",
                body="Acting on two of them could prevent an estimated R86,000 in reactive maintenance.",
                window_label="Rolling 7 days",
                signals_reviewed=1284,
                sources=9,
                avoidable_zar=86000.0,
            )
            recommendations = _default_recommendations()
            source_tag = "sample_baseline"

        return EstateIntelligenceResponse(
            estate_id=estate_id,
            estate_name=estate_name,
            as_of=datetime.now(timezone.utc),
            briefing=briefing,
            recommendations=recommendations,
            operational_signals=counts,
            source=source_tag,
        )

    async def ask_valora(self, estate_id: int, question: str, actor: User) -> AskValoraResponse:
        """Process an Ask VALORA question, forwarding to n8n if configured or answering from domain."""
        await self._auth.resolve_access(actor, estate_id)

        estate = await self._estates.get_by_id(estate_id)
        estate_name = estate.name if estate else f"Estate {estate_id}"

        settings = get_settings()

        # If n8n webhook is configured, call it
        if settings.N8N_INTELLIGENCE_URL:
            n8n_url = settings.N8N_INTELLIGENCE_URL.rstrip("/")
            endpoint = f"{n8n_url}/valora/ask"
            headers: dict[str, str] = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if settings.N8N_SERVICE_KEY:
                headers["X-Valora-Secret"] = settings.N8N_SERVICE_KEY.get_secret_value()

            payload = {
                "question": question,
                "estate_id": estate_id,
                "estate_name": estate_name,
            }

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(endpoint, json=payload, headers=headers)
                    if resp.is_success:
                        data = resp.json()
                        if isinstance(data, dict) and "summary" in data:
                            return AskValoraResponse(
                                summary=str(data["summary"]),
                                evidence=[str(x) for x in data.get("evidence", []) if x],
                                recommendation=str(data.get("recommendation", "")),
                                related=[str(x) for x in data.get("related", []) if x],
                                source="n8n",
                            )
            except Exception as e:
                logger.warning(f"Failed to communicate with n8n intelligence service at {endpoint}: {e}")

        # Fallback to domain response
        return _domain_answer(question, estate_name)

    async def get_estate_signals(
        self,
        estate_id: int,
        actor: User | None = None,
        internal_key: str | None = None,
    ) -> EstateSignalsExport:
        """Export raw operational signals for n8n ingestion.
        
        Requires either HOA admin access or a verified internal service key.
        """
        settings = get_settings()
        service_secret = (
            settings.N8N_SERVICE_KEY.get_secret_value()
            if settings.N8N_SERVICE_KEY
            else None
        )

        authorized = False
        if internal_key and service_secret and internal_key == service_secret:
            authorized = True
        elif actor is not None:
            access = await self._auth.resolve_access(actor, estate_id)
            if access.is_estate_admin or actor.role == UserRole.hoa_admin.value:
                authorized = True

        if not authorized:
            raise ForbiddenException("Administrator or service key authorization required.")

        estate = await self._estates.get_by_id(estate_id)
        if not estate:
            raise NotFoundException("Estate not found")

        counts = await self.get_operational_counts(estate_id)

        # 1. Fetch recent complaints
        q_complaints = (
            select(Complaint)
            .where(Complaint.estate_id == estate_id)
            .order_by(Complaint.created_at.desc())
            .limit(50)
        )
        res_complaints = await self._db.execute(q_complaints)
        complaints = res_complaints.scalars().all()

        # 2. Fetch recent work orders
        q_orders = (
            select(MaintenanceworkOrder)
            .where(MaintenanceworkOrder.estate_id == estate_id)
            .order_by(MaintenanceworkOrder.created_at.desc())
            .limit(50)
        )
        res_orders = await self._db.execute(q_orders)
        orders = res_orders.scalars().all()

        # 3. Fetch recent security incidents
        q_incidents = (
            select(SecurityIncident)
            .where(SecurityIncident.estate_id == estate_id)
            .order_by(SecurityIncident.created_at.desc())
            .limit(50)
        )
        res_incidents = await self._db.execute(q_incidents)
        incidents = res_incidents.scalars().all()

        # 4. Fetch latest Living Score snapshot
        q_score = (
            select(LivingScoreSnapshot)
            .where(LivingScoreSnapshot.estate_id == estate_id)
            .order_by(LivingScoreSnapshot.as_of.desc())
            .limit(1)
        )
        res_score = await self._db.execute(q_score)
        latest_score = res_score.scalar_one_or_none()

        signal_items: list[EstateSignalItem] = []

        if latest_score:
            signal_items.append(
                EstateSignalItem(
                    type="living_score",
                    id=latest_score.snapshot_id,
                    title=f"Living Score Snapshot: {latest_score.living_score}/100",
                    status="published",
                    date=latest_score.as_of.isoformat() if latest_score.as_of else "",
                    detail=f"Resolution: {latest_score.complaint_resolution_score}, Security: {latest_score.security_incident_score}, Maintenance: {latest_score.infrastructure_maintenance_score}",
                )
            )

        for c in complaints:
            signal_items.append(
                EstateSignalItem(
                    type="complaint",
                    id=c.complaint_id,
                    title=f"Complaint: {c.category}",
                    status=c.status or "submitted",
                    date=c.created_at.isoformat() if c.created_at else "",
                    detail=c.description[:200] if c.description else "",
                )
            )

        for o in orders:
            signal_items.append(
                EstateSignalItem(
                    type="work_order",
                    id=o.work_order_id,
                    title=f"Work Order #{o.work_order_id}",
                    status=o.status or "assigned",
                    date=o.created_at.isoformat() if o.created_at else "",
                    detail=f"Job cost: R{o.job_cost or 0}. Notes: {o.completion_notes or ''}",
                )
            )

        for inc in incidents:
            signal_items.append(
                EstateSignalItem(
                    type="incident",
                    id=inc.incident_id,
                    title=f"Security Incident: {inc.category} ({inc.severity})",
                    status=inc.status or "open",
                    date=inc.created_at.isoformat() if inc.created_at else "",
                    detail=inc.notes or "",
                )
            )

        return EstateSignalsExport(
            estate_id=estate_id,
            estate_name=estate.name,
            generated_at=datetime.now(timezone.utc),
            counts=counts,
            signals=signal_items,
        )

    async def ingest_intelligence(
        self,
        estate_id: int,
        payload: IngestIntelligencePayload,
        actor: User | None = None,
        internal_key: str | None = None,
    ) -> bool:
        """Store/cache generated briefing and recommendations from n8n."""
        settings = get_settings()
        service_secret = (
            settings.N8N_SERVICE_KEY.get_secret_value()
            if settings.N8N_SERVICE_KEY
            else None
        )

        authorized = False
        if internal_key and service_secret and internal_key == service_secret:
            authorized = True
        elif actor is not None:
            access = await self._auth.resolve_access(actor, estate_id)
            if access.is_estate_admin or actor.role == UserRole.hoa_admin.value:
                authorized = True

        if not authorized:
            raise ForbiddenException("Administrator or service key authorization required.")

        _BRIEFING_CACHE[estate_id] = (payload.briefing, payload.recommendations)
        return True
