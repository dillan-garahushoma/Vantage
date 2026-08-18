"""SQLAlchemy declarative base.

Import Base from here in all ORM model files.
Alembic env.py also imports Base.metadata from here.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
