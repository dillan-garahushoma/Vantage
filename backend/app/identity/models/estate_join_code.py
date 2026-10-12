from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    TIMESTAMP,
    UniqueConstraint,
    text,
)
from sqlalchemy.sql import func

from app.db.base import Base


class EstateJoinCode(Base):
    """A shareable secret that admits one resident to one estate.

    The code is stored in clear text on purpose: an HOA admin has to be able to
    read it back from ``GET /api/v1/join-codes/current`` and send it to a new
    resident. It is therefore a secret in the sense of a password-reset link, not
    a stored credential - and it is never placed in a URL, a log line or an error
    message (see ADR-007).

    Uniqueness rules: every ``code`` is unique for all time, so a leaked code can
    never become valid again through a later draw, and a partial unique index
    permits at most one un-revoked code per estate, so rotation can never leave
    two live codes behind.
    """

    __tablename__ = "estate_join_codes"
    __table_args__ = (
        UniqueConstraint("code", name="uq_estate_join_codes_code"),
        Index(
            "uq_estate_join_codes_one_active_per_estate",
            "estate_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    code_id = Column(Integer, primary_key=True, index=True)
    estate_id = Column(
        Integer, ForeignKey("estates.estate_id", ondelete="RESTRICT"), nullable=False
    )
    code = Column(String(12), nullable=False)
    # The admin who issued it; nulled if that account is later deleted.
    created_by = Column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    # Null means the code never expires; revoked is distinct from expired.
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)
