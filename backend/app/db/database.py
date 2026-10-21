"""Alembic model registry.

This module must import every ORM model so that Base.metadata is fully populated
when Alembic generates or runs migrations. Add new models here as they are created.
"""

# pylint: disable=unused-import
from app.db.base import Base  # noqa: F401 — ensures metadata is available

# Identity domain
from app.identity.models.estate_membership import EstateMembership  # noqa: F401
from app.identity.models.estate_join_code import EstateJoinCode  # noqa: F401
from app.identity.models.estate_membership_event import EstateMembershipEvent  # noqa: F401
from app.identity.models.estate_residency_request import EstateResidencyRequest  # noqa: F401
from app.identity.models.user import User  # noqa: F401
from app.identity.models.session import Session  # noqa: F401
from app.identity.models.login_attempt import LoginAttempts  # noqa: F401

# Property domain
from app.property.models.estate import Estate  # noqa: F401
from app.property.models.estate_photo import EstatePhoto  # noqa: F401
from app.property.models.property import Property  # noqa: F401
from app.property.models.investment_scenario import InvestmentScenario  # noqa: F401
from app.property.models.market import (  # noqa: F401
    MarketingAuthority, MarketingRequest, MarketListing,
    ListingPriceEvent, MarketTransaction, MarketEvent,
)
from app.property.models.listing import Listing  # noqa: F401
from app.property.models.sale import Sale  # noqa: F401

# Community domain
from app.community.models.complaint import Complaint  # noqa: F401
from app.community.models.complaint_ai_suggestion import ComplaintAISuggestion  # noqa: F401
from app.community.models.complaint_event import ComplaintEvent  # noqa: F401
from app.community.models.maintenance_work_order import MaintenanceworkOrder  # noqa: F401
from app.community.models.announcement import Announcement  # noqa: F401
from app.community.models.security_incident import SecurityIncident  # noqa: F401

# Providers domain
from app.providers.models.service_provider import ServiceProvider  # noqa: F401
from app.providers.models.review import Review  # noqa: F401

# Analytics domain
from app.analytics.models.ai_analytic import AIAnalytic  # noqa: F401
from app.analytics.models.intelligence_briefing import IntelligenceBriefing  # noqa: F401
from app.analytics.models.ai_call_event import AICallEvent  # noqa: F401
from app.analytics.models.ai_insight import AIInsight  # noqa: F401
from app.analytics.models.ai_insight_feedback import AIInsightFeedback  # noqa: F401
from app.analytics.models.living_score_snapshot import LivingScoreSnapshot  # noqa: F401

# Contact domain
from app.contact.models.contact_message import ContactMessage  # noqa: F401

