from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.sql import func

from app.community.domain.incident_vocabulary import (
    CATEGORIES,
    DEFAULT_STATUS,
    SEVERITIES,
    STATUSES,
    resolution_timestamps_check,
    sql_in,
)
from app.db.base import Base


class SecurityIncident(Base):
    """One estate-scoped security incident.

    Deliberately small: the only product use is the Living Score security input
    (a count of incidents in a window), so there is no assignment, comment,
    attachment, notification or workflow here, and no description field. Every
    text column is an operator note, never resident-written text.

    ``estate_id`` is the tenant boundary and every read is scoped by it.
    """

    __tablename__ = "security_incidents"

    incident_id = Column(Integer, primary_key=True, index=True)
    estate_id = Column(
        Integer,
        ForeignKey(
            "estates.estate_id",
            ondelete="RESTRICT",
            name="fk_security_incidents_estate_id_estates",
        ),
        nullable=False,
    )
    # Optional: an incident may be estate-wide (the perimeter, the gate) rather
    # than tied to a unit, and a unit may be removed without erasing history.
    property_id = Column(
        Integer,
        ForeignKey(
            "properties.unit_id",
            ondelete="SET NULL",
            name="fk_security_incidents_property_id_properties",
        ),
        nullable=True,
    )
    category = Column(String(32), nullable=False)
    severity = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, server_default=DEFAULT_STATUS)
    occurred_at = Column(TIMESTAMP(timezone=True), nullable=False)
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_by = Column(
        Integer,
        ForeignKey(
            "users.user_id",
            ondelete="SET NULL",
            name="fk_security_incidents_created_by_users",
        ),
        nullable=True,
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(sql_in("category", CATEGORIES), name="ck_security_incidents_category"),
        CheckConstraint(sql_in("severity", SEVERITIES), name="ck_security_incidents_severity"),
        CheckConstraint(sql_in("status", STATUSES), name="ck_security_incidents_status"),
        CheckConstraint(
            resolution_timestamps_check(),
            name="ck_security_incidents_resolution_timestamps",
        ),
        # The Living Score security input: "how many incidents in this estate in
        # the last 90 days?".
        Index("ix_security_incidents_estate_id_occurred_at", "estate_id", "occurred_at"),
        # The HOA list view: "what is still open in this estate?".
        Index("ix_security_incidents_estate_id_status", "estate_id", "status"),
    )
