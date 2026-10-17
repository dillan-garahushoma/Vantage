"""Schemas describing the estates a caller may access.

The estate is the tenant boundary. A client must never be trusted to supply an
``estate_id``; it must choose from this server-resolved list.
"""
from pydantic import BaseModel, Field


class EstateAccessResponse(BaseModel):
    """One estate the authenticated user has a persisted membership in."""

    estate_id: int
    estate_name: str
    suburb: str
    city: str
    province: str
    membership_roles: list[str]
    property_ids: list[int]
    is_estate_admin: bool
    is_estate_provider: bool
    # True for a seeded demonstration estate; the client must label it as such.
    is_demo: bool = False


class EstateAccessListResponse(BaseModel):
    """All estates the caller can select. Empty means provisioning is pending."""

    estates: list[EstateAccessResponse] = Field(default_factory=list)
