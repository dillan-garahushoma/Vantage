"""Security incident use cases (BATCH 6B).

Intentionally small: an HOA admin records an incident, and anyone in the estate
can see that it happened. There is no assignment, no comment thread, no
notification and no delete - the only downstream consumer is the Living Score
security input, which counts incidents in a window.

Authorization is `hoa_admin` **and** a matching estate membership for writes,
via `EstateAuthorizationService`; reads need membership only. The estate is
never taken from the request body.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utcnow
from app.common.enums import UserRole
from app.common.pagination import Page
from app.community.domain.incident_vocabulary import (
    DEFAULT_STATUS,
    INVESTIGATING_STATUS,
    RESOLVED_STATUS,
)
from app.community.models.security_incident import SecurityIncident
from app.community.repositories.security_incident_repository import (
    SecurityIncidentRepository,
)
from app.community.schemas.security_incident import (
    IncidentCreate,
    IncidentResponse,
    IncidentUpdate,
)
from app.core.exceptions import ConflictException, NotFoundException
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.repositories.property_repository import PropertyRepository

# open -> investigating -> resolved, and open -> resolved. `resolved` is terminal
# (see the open question in docs/progress/batch-6b.md).
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    DEFAULT_STATUS: frozenset({INVESTIGATING_STATUS, RESOLVED_STATUS}),
    INVESTIGATING_STATUS: frozenset({RESOLVED_STATUS}),
}


class SecurityIncidentService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = SecurityIncidentRepository(db)
        self._property_repo = PropertyRepository(db)
        self._estate_authorization = EstateAuthorizationService(db)

    # ---- helpers -------------------------------------------------------

    @staticmethod
    def _to_response(incident: SecurityIncident, *, is_estate_admin: bool) -> IncidentResponse:
        """Serialise one incident for one viewer.

        A member who is not an estate admin sees that the incident happened and
        what it was, but not the unit it is attached to, the operator's notes or
        who recorded it. The keys stay present and null.
        """
        response = IncidentResponse.model_validate(incident)
        if not is_estate_admin:
            response.property_id = None
            response.resolution_notes = None
            response.created_by = None
        return response

    async def _get_or_404(self, *, incident_id: int, estate_id: int) -> SecurityIncident:
        incident = await self._repo.get_by_id_in_estate(
            incident_id=incident_id, estate_id=estate_id
        )
        if incident is None:
            raise NotFoundException(f"Incident with id {incident_id} was not found.")
        return incident

    # ---- use cases -----------------------------------------------------

    async def create_incident(
        self, payload: IncidentCreate, admin: User, *, estate_id: int
    ) -> IncidentResponse:
        await self._estate_authorization.require_role(
            actor=admin, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,)
        )
        if payload.property_id is not None:
            property_ = await self._property_repo.get_by_id_in_estate(
                unit_id=payload.property_id, estate_id=estate_id
            )
            if property_ is None:
                # A unit in another estate must look absent, not forbidden.
                raise NotFoundException(f"Property with id {payload.property_id} was not found.")

        incident = await self._repo.create(
            estate_id=estate_id,
            property_id=payload.property_id,
            category=payload.category,
            severity=payload.severity,
            status=DEFAULT_STATUS,
            occurred_at=payload.occurred_at,
            created_by=admin.user_id,
        )
        return self._to_response(incident, is_estate_admin=True)

    async def update_incident(
        self,
        incident_id: int,
        payload: IncidentUpdate,
        admin: User,
        *,
        estate_id: int,
    ) -> IncidentResponse:
        await self._estate_authorization.require_role(
            actor=admin, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,)
        )
        incident = await self._get_or_404(incident_id=incident_id, estate_id=estate_id)

        if incident.status == RESOLVED_STATUS:
            raise ConflictException(
                f"Incident {incident_id} is resolved and can no longer be changed."
            )

        changes = payload.model_dump(exclude_unset=True)

        new_status = changes.get("status")
        if new_status is not None and new_status != incident.status:
            allowed = _ALLOWED_TRANSITIONS.get(incident.status or "", frozenset())
            if new_status not in allowed:
                raise ConflictException(
                    f"Incident cannot transition from {incident.status} to {new_status}."
                )
            incident.status = new_status
            if new_status == RESOLVED_STATUS:
                # Server-side, never client-supplied.
                incident.resolved_at = utcnow()

        if changes.get("severity") is not None:
            incident.severity = changes["severity"]
        if "resolution_notes" in changes:
            incident.resolution_notes = changes["resolution_notes"]

        incident = await self._repo.save(incident)
        return self._to_response(incident, is_estate_admin=True)

    async def list_incidents(
        self,
        actor: User,
        *,
        page: int,
        size: int,
        estate_id: int,
        status: str | None = None,
        severity: str | None = None,
        category: str | None = None,
        occurred_from=None,
        occurred_to=None,
    ) -> Page[IncidentResponse]:
        access = await self._estate_authorization.resolve_access(actor, estate_id)
        filters = dict(
            estate_id=estate_id,
            status=status,
            severity=severity,
            category=category,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )
        incidents = await self._repo.search(offset=(page - 1) * size, limit=size, **filters)
        total = await self._repo.count(**filters)
        return Page[IncidentResponse](
            items=[
                self._to_response(i, is_estate_admin=access.is_estate_admin) for i in incidents
            ],
            total=total,
            page=page,
            size=size,
        )

    async def get_incident(
        self, incident_id: int, actor: User, *, estate_id: int
    ) -> IncidentResponse:
        access = await self._estate_authorization.resolve_access(actor, estate_id)
        incident = await self._get_or_404(incident_id=incident_id, estate_id=estate_id)
        return self._to_response(incident, is_estate_admin=access.is_estate_admin)
