from sqlalchemy import Boolean, Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func

from app.db.base import Base


class LoginAttempts(Base):
    __tablename__ = "login_attempts"

    attempt_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255))
    ip_address = Column(String(45))
    successful = Column(Boolean)
    attempted_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
