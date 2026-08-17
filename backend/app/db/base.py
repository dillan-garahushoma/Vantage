"""
Database base module.
Imports all entity modules so that SQLAlchemy's metadata is fully populated
before Alembic autogenerate runs. Add new entity imports here as domains grow.
"""

# Re-export Base so alembic/env.py only needs to import from one place.
from app.db.session import Base  # noqa: F401

# ---------------------------------------------------------------------------
# Entity imports — all entities.py files listed here so Alembic can
# discover them during `alembic revision --autogenerate`.
# ---------------------------------------------------------------------------
from app.identity.domain import entities as _identity_entities  # noqa: F401
from app.property.domain import entities as _property_entities  # noqa: F401
from app.community.domain import entities as _community_entities  # noqa: F401
from app.providers.domain import entities as _providers_entities  # noqa: F401
from app.analytics.domain import entities as _analytics_entities  # noqa: F401
