from enum import Enum


class UserRole(str, Enum):
    """VALORA user roles for RBAC."""
    casual_visitor = "casual_visitor"
    resident = "resident"
    investor = "investor"
    estate_agent = "estate_agent"
    hoa_admin = "hoa_admin"
    service_provider = "service_provider"


class ComplaintStatus(str, Enum):
    submitted = "submitted"
    reviewed = "reviewed"
    assigned = "assigned"
    in_progress = "in_progress"
    resolved = "resolved"
    rated = "rated"
    # Retained only so existing legacy records can still be read.
    closed = "closed"


class WorkOrderStatus(str, Enum):
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class ListingStatus(str, Enum):
    active = "active"
    sold = "sold"
    withdrawn = "withdrawn"
