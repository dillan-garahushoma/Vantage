from sqlalchemy import Boolean, Column, Integer, String, Text, TIMESTAMP, false
from sqlalchemy.sql import func

from app.db.base import Base


class Estate(Base):
    """The tenant and operational-health boundary for VALORA data."""

    __tablename__ = "estates"

    estate_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False, unique=True)
    suburb = Column(String(120), nullable=False)
    city = Column(String(120), nullable=False)
    province = Column(String(80), nullable=False)
    description = Column(Text, nullable=True)
    # Seeded demonstration estate: never treated as a real customer's data.
    is_demo = Column(Boolean, nullable=False, server_default=false())
    # May this estate appear in the unauthenticated public directory? Default
    # false: publishing is a deliberate act by the estate's administrator.
    is_public = Column(Boolean, nullable=False, server_default=false())
    # May the public detail page expose the latest stored Living Score? Separate
    # from is_public: photos and an operational-health number are different
    # decisions.
    show_living_score = Column(Boolean, nullable=False, server_default=false())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
