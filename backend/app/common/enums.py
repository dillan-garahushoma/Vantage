"""
Shared enumerations used across multiple domains.
"""
import enum


class UserRole(str, enum.Enum):
    """System-wide user roles."""

    RESIDENT = "resident"
    HOA_ADMIN = "hoa_admin"
    INVESTOR = "investor"
    PROVIDER = "provider"
    SUPER_ADMIN = "super_admin"


class ComplaintStatus(str, enum.Enum):
    """Lifecycle states for a maintenance complaint."""

    OPEN = "open"
    UNDER_REVIEW = "under_review"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CLOSED = "closed"
    REJECTED = "rejected"


class PropertyType(str, enum.Enum):
    """Classification of a property unit."""

    APARTMENT = "apartment"
    TOWNHOUSE = "townhouse"
    FREESTANDING = "freestanding"
    PENTHOUSE = "penthouse"
    COMMERCIAL = "commercial"


class ProviderStatus(str, enum.Enum):
    """Verification status of a service provider."""

    PENDING = "pending"
    VERIFIED = "verified"
    SUSPENDED = "suspended"
    REJECTED = "rejected"
