"""
Providers domain — ORM entity definitions.
Entities: ServiceProvider.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import ProviderStatus
from app.db.session import Base


class ServiceProvider(Base):
    """A third-party service provider (plumber, electrician, etc.) registered on VALORA."""

    __tablename__ = "service_providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_category: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProviderStatus] = mapped_column(
        Enum(ProviderStatus, name="provider_status"),
        nullable=False,
        default=ProviderStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<ServiceProvider id={self.id} company={self.company_name} status={self.status}>"
