"""The public directory's allow-list contracts.

These DTOs are reachable **without authentication**, so every field here is a
deliberate publication decision. They are write-once allow-lists: unit numbers,
street addresses, member names, emails, complaint text, incident reports, join
codes and internal ids (the numeric ``estate_id`` of a photo row, the uploader)
are not "omitted by default" - they are not representable in this module at all.
A test asserts the exact key set of each response so that adding a field to an
internal DTO can never leak through here.

What is published: the estate's name, where it is (suburb/city/province - a
complex's location is already public information), its own description, how many
units it has, the ``public_id`` of its photos, and - only when the estate has
opted in (``show_living_score``) and a snapshot exists - a four-field summary of
the latest stored Living Score.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PublicPhotoResponse(BaseModel):
    """One photo of a public estate: the unguessable handle and its caption."""

    public_id: str
    caption: str | None


class PublicEstateListItem(BaseModel):
    """One row of the public grid."""

    estate_id: int
    name: str
    suburb: str
    city: str
    province: str
    description: str | None
    unit_count: int
    cover_photo_public_id: str | None


class PublicLivingScoreSummary(BaseModel):
    """Four fields of the latest stored snapshot, and nothing else.

    ``data_origin`` is ``"demo"`` for a seeded demonstration estate (the frontend
    has to badge that honestly) and ``"live"`` otherwise. The per-component
    breakdown, the drivers and the raw inputs stay internal: they are operational
    detail about a private community.
    """

    overall_score: Decimal | None
    status: str
    as_of: datetime
    engine_version: str
    data_origin: str


class PublicEstateDetailResponse(BaseModel):
    """The public detail page for one published estate."""

    estate_id: int
    name: str
    suburb: str
    city: str
    province: str
    description: str | None
    unit_count: int
    photos: list[PublicPhotoResponse] = Field(default_factory=list)
    living_score: PublicLivingScoreSummary | None = None
