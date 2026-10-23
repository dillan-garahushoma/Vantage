"""Estate-scoped signal reads and append-only briefing persistence. Flush only."""
from datetime import datetime, timezone
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models.intelligence_briefing import IntelligenceBriefing
from app.analytics.models.living_score_snapshot import LivingScoreSnapshot
from app.community.models.complaint import Complaint
from app.community.models.maintenance_work_order import MaintenanceworkOrder
from app.community.models.security_incident import SecurityIncident


class IntelligenceRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def maintenance_priorities(self, estate_id: int, as_of) -> list[dict]:
        """Bounded metadata only; overdue jobs first, then unassigned urgent issues."""
        wo = MaintenanceworkOrder
        rows = (await self._db.execute(select(wo.work_order_id, wo.estimated_completion_date,
            wo.status).where(wo.estate_id == estate_id, wo.status.in_(['assigned', 'in_progress']),
                wo.estimated_completion_date < as_of).order_by(
                    wo.estimated_completion_date, wo.work_order_id).limit(20))).all()
        results = [dict(kind='overdue_work_order', id=row[0], due_at=row[1].isoformat(),
                        status=row[2]) for row in rows]
        rows = (await self._db.execute(select(Complaint.complaint_id, Complaint.priority,
            Complaint.created_at).where(Complaint.estate_id == estate_id,
                Complaint.status.in_(['submitted', 'reviewed']),
                Complaint.priority.in_(['urgent', 'high'])).order_by(
                    case((Complaint.priority == 'urgent', 0), else_=1),
                    Complaint.created_at, Complaint.complaint_id).limit(20))).all()
        results.extend(dict(kind='unassigned_complaint', id=row[0], priority=row[1],
                            created_at=row[2].isoformat()) for row in rows)
        return results

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

    async def resident_signals(self, estate_id: int, user_id: int) -> list[dict]:
        """Fetch recent complaints logged by this user for this estate."""
        rows = (await self._db.execute(select(
            Complaint.complaint_id, Complaint.category, Complaint.description,
            Complaint.status, Complaint.created_at,
        ).where(
            Complaint.estate_id == estate_id,
            Complaint.user_id == user_id,
        ).order_by(Complaint.created_at.desc()).limit(15))).all()
        return [
            {
                "id": row[0],
                "category": row[1] or "General",
                "title": (row[2][:60] + "...") if len(row[2]) > 60 else row[2],
                "status": row[3] or "submitted",
                "logged_date": row[4].isoformat() if row[4] else "",
            }
            for row in rows
        ]

    async def provider_signals(self, estate_id: int, user_id: int) -> list[dict]:
        """Fetch active work orders assigned to this provider for this estate."""
        from app.providers.models.service_provider import ServiceProvider
        p_row = (await self._db.execute(
            select(ServiceProvider.provider_id).where(ServiceProvider.user_id == user_id)
        )).scalar_one_or_none()

        wo = MaintenanceworkOrder
        query = select(
            wo.work_order_id,
            wo.status,
            wo.estimated_completion_date,
            wo.assigned_at,
        ).where(
            wo.estate_id == estate_id,
            wo.status.in_(["assigned", "in_progress", "pending"]),
        )
        if p_row is not None:
            query = query.where(wo.provider_id == p_row)

        now = datetime.now(timezone.utc)
        rows = (await self._db.execute(
            query.order_by(wo.estimated_completion_date.asc().nulls_last(), wo.work_order_id.desc()).limit(20)
        )).all()
        return [
            {
                "id": row[0],
                "title": f"Work Order #{row[0]}",
                "priority": "high" if row[2] and row[2] < now else "medium",
                "status": row[1] or "assigned",
                "location": "Estate maintenance zone",
                "due_date": row[2].isoformat() if row[2] else None,
            }
            for row in rows
        ]

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
