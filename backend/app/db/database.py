"""Alembic model registry.

This module must import every ORM model so that Base.metadata is fully populated
when Alembic generates or runs migrations. Add new models here as they are created.
"""

# pylint: disable=unused-import
from app.db.base import Base  # noqa: F401 — ensures metadata is available

# Identity domain
from app.identity.models.user import User  # noqa: F401
from app.identity.models.session import Session  # noqa: F401
from app.identity.models.login_attempt import LoginAttempts  # noqa: F401

# Property domain
from app.property.models.property import Property  # noqa: F401
from app.property.models.listing import Listing  # noqa: F401
from app.property.models.sale import Sale  # noqa: F401

# Community domain
from app.community.models.complaint import Complaint  # noqa: F401
from app.community.models.maintenance_work_order import MaintenanceworkOrder  # noqa: F401
from app.community.models.announcement import Announcement  # noqa: F401

# Providers domain
from app.providers.models.service_provider import ServiceProvider  # noqa: F401
from app.providers.models.review import Review  # noqa: F401

# Analytics domain
from app.analytics.models.ai_analytic import AIAnalytic  # noqa: F401
