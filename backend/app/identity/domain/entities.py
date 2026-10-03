"""Identity domain entities.

These are pure Python dataclasses/models representing business concepts,
decoupled from the SQLAlchemy persistence layer.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class UserEntity:
    """Represents an authenticated user in the identity domain."""
    user_id: int
    email: str
    full_name: str
    role: str
    unit_no: str | None
    email_verified: bool
    hoa_approved: bool
    created_at: datetime
