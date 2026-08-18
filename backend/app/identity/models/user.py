from sqlalchemy import Boolean, Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phoneno = Column(String(20))
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    unit_no = Column(String(10))
    verification_token = Column(String(255))
    email_verified = Column(Boolean, default=False)
    hoa_approved = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
