"""Estate-scoped signal reads and append-only briefing persistence. Flush only."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models.intelligence_briefing import IntelligenceBriefing
from app.analytics.models.living_score_snapshot import LivingScoreSnapshot
from app.community.models.complaint import Complaint
from app.community.models.maintenance_work_order import MaintenanceworkOrder
from app.community.models.security_incident import SecurityIncident


class IntelligenceRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def facts(self, estate_id: int) -> dict:
        # Scalar subqueries keep all counts and score comparisons in ONE PostgreSQL
        # statement snapshot. Counts cover all matching rows, not the export page.
        counts = []
        for model, condition in (
            (Complaint, Complaint.status.in_(['submitted', 'reviewed', 'assigned', 'in_progress'])),
            (MaintenanceworkOrder, MaintenanceworkOrder.status.in_(['assigned', 'in_progress'])),
            (SecurityIncident, SecurityIncident.status != 'resolved'),
        ):
            counts.append(select(func.count()).select_from(model).where(
                model.estate_id == estate_id, condition).scalar_subquery())
        score = LivingScoreSnapshot
        score_order = [score.as_of.desc(), score.snapshot_id.desc()]
        # Retain an insufficient-data latest row; do not substitute an older score.
        score_json = func.jsonb_build_object(
            'snapshot_id', score.snapshot_id, 'as_of', score.as_of,
            'status', score.status, 'overall_score', score.overall_score,
            'engine_version', score.engine_version)
        snapshots = [select(score_json).where(score.estate_id == estate_id).order_by(
            *score_order).offset(offset).limit(1).scalar_subquery() for offset in (0, 1)]
        row = (await self._db.execute(select(*counts, *snapshots))).one()
        return {'counts': dict(zip(('open_complaints', 'work_orders_in_flight', 'unresolved_incidents'), row[:3])),
                'latest_score': row[3], 'previous_score': row[4]}

    async def recent_signals(self, estate_id: int, limit: int = 50) -> list[dict]:
        items = []
        for model, id_column, kind in (
            (Complaint, Complaint.complaint_id, 'complaint'),
            (MaintenanceworkOrder, MaintenanceworkOrder.work_order_id, 'work_order'),
            (SecurityIncident, SecurityIncident.incident_id, 'incident'),
        ):
            rows = (await self._db.execute(select(id_column, model.status, model.created_at).where(
                model.estate_id == estate_id).order_by(model.created_at.desc(), id_column.desc()).limit(limit))).all()
            items.extend({'type': kind, 'id': ident, 'status': status or '',
                          'title': f'{kind} #{ident}', 'date': created.isoformat() if created else '',
                          'detail': ''} for ident, status, created in rows)
        return items

    async def add(self, **values) -> IntelligenceBriefing:
        row = IntelligenceBriefing(**values)
        self._db.add(row)
        await self._db.flush()
        return row

    async def get(self, estate_id: int, briefing_id: int) -> IntelligenceBriefing | None:
        return (await self._db.execute(select(IntelligenceBriefing).where(
            IntelligenceBriefing.estate_id == estate_id,
            IntelligenceBriefing.briefing_id == briefing_id))).scalar_one_or_none()

    async def history(self, estate_id: int, *, offset: int, limit: int) -> tuple[list[IntelligenceBriefing], int]:
        total = (await self._db.execute(select(func.count()).select_from(IntelligenceBriefing).where(
            IntelligenceBriefing.estate_id == estate_id))).scalar_one()
        rows = (await self._db.execute(select(IntelligenceBriefing).where(
            IntelligenceBriefing.estate_id == estate_id).order_by(
                IntelligenceBriefing.created_at.desc(), IntelligenceBriefing.briefing_id.desc())
            .offset(offset).limit(limit))).scalars().all()
        return list(rows), total
