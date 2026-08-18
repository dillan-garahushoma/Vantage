"""Community domain entities — pure business concepts decoupled from the ORM."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ComplaintEntity:
    complaint_id: int
    user_id: int
    unit_id: int
    category: str
    description: str
    is_anonymous: bool
    status: str
    created_at: datetime


@dataclass
class AnnouncementEntity:
    announcement_id: int
    title: str
    message: str
    created_by: int
    created_at: datetime
