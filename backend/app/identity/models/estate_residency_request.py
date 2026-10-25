from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    TIMESTAMP,
    text,
)
from sqlalchemy.sql import func

from app.db.base import Base

#: The applicant's contact snapshot length. 320 is the maximum practical email
#: length (RFC 5321 forward-path); the name and phone bounds match the users row.
APPLICANT_NAME_MAX_LENGTH = 120
APPLICANT_EMAIL_MAX_LENGTH = 320
APPLICANT_PHONE_MAX_LENGTH = 32
UNIT_NO_MAX_LENGTH = 10
NOTE_MAX_LENGTH = 500


class EstateResidencyRequest(Base):
    """A resident's request to be admitted to one estate, optionally one unit.

    This is the approval-based counterpart to redeeming a join code. A resident
    submits it, an ``hoa_admin`` of the same estate decides it, and only an
    approval produces a membership row. The request is therefore the audit record
    of *who asked, who decided and when* - which is why it is never deleted and
    why it carries the applicant's contact details as they were at submission
    time, not as a foreign key that a later account deletion would empty.

    ``decided_by`` is ``SET NULL`` for the same reason the membership event log
    uses it: removing an administrator's account must not erase the fact that a
    decision was made. ``decided_at`` is the durable half of that pair, and the
    check constraint makes the two states the only representable ones: a pending
    request has never been decided, and a decided request always carries a time.

    Uniqueness: at most one *pending* request per user per estate (a partial
    unique index), so a resident cannot queue duplicates, while a rejected
    resident may still apply again later.
    """

    __tablename__ = "estate_residency_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_estate_residency_requests_status",
        ),
        CheckConstraint(
            "status = 'pending' OR decided_at IS NOT NULL",
            name="ck_estate_residency_requests_decided_at_present",
        ),
        CheckConstraint(
            "status <> 'pending' OR decided_at IS NULL",
            name="ck_estate_residency_requests_pending_undecided",
        ),
        Index(
            "uq_estate_residency_requests_one_pending_per_user_estate",
            "user_id",
            "estate_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "ix_estate_residency_requests_estate_id_status_created_at",
            "estate_id",
            "status",
            "created_at",
        ),
    )

    request_id = Column(Integer, primary_key=True, index=True)
    estate_id = Column(
        Integer, ForeignKey("estates.estate_id", ondelete="RESTRICT"), nullable=False
    )
    # The applicant's account; nulled if the account is deleted, so the request
    # survives for the estate's records.
    user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    property_id = Column(
        Integer, ForeignKey("properties.unit_id", ondelete="SET NULL"), nullable=True
    )
    # The unit number as submitted, kept as text so the request still reads
    # correctly if the unit row is later removed or renamed.
    unit_no = Column(String(UNIT_NO_MAX_LENGTH), nullable=True)
    status = Column(String(16), nullable=False, server_default="pending")

    # The applicant's identity at submission time. Read by the HOA notification
    # and by the admin list; never joined live from ``users`` so a deleted account
    # cannot blank out the request.
    applicant_name = Column(String(APPLICANT_NAME_MAX_LENGTH), nullable=False)
    applicant_email = Column(String(APPLICANT_EMAIL_MAX_LENGTH), nullable=False)
    applicant_phone = Column(String(APPLICANT_PHONE_MAX_LENGTH), nullable=True)
    note = Column(String(NOTE_MAX_LENGTH), nullable=True)

    decided_by = Column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    decided_at = Column(TIMESTAMP(timezone=True), nullable=True)
    decision_note = Column(String(NOTE_MAX_LENGTH), nullable=True)

    # Idempotence guards for the two best-effort notification emails: only a
    # successful send sets the timestamp, so a retried event never emails twice.
    notified_at = Column(TIMESTAMP(timezone=True), nullable=True)
    decision_notified_at = Column(TIMESTAMP(timezone=True), nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
