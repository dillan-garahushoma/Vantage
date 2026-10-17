"""Estate profile and photo contracts.

Two audiences again:

* the administer-your-own-estate DTOs (``EstateProfileResponse``,
  ``EstateProfileUpdate``, ``EstatePhotoResponse``) - a member may read the
  profile, an ``hoa_admin`` of that estate may change it;
* nothing public lives here. The public directory has its own allow-list
  (``app/property/schemas/public_directory.py``) so it can never grow a field by
  accident because an internal DTO did.

``EstateProfileUpdate`` deliberately has **no name field**: renaming an estate is
not in this batch and an extra field is rejected outright (``extra="forbid"``),
which is what makes that guarantee testable.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.property.models.estate_photo import PHOTO_CAPTION_MAX_LENGTH


class EstateProfileResponse(BaseModel):
    """The profile an estate's members can read."""

    estate_id: int
    name: str
    suburb: str
    city: str
    province: str
    description: str | None
    is_public: bool
    show_living_score: bool
    is_demo: bool

    model_config = ConfigDict(from_attributes=True)


class EstateProfileUpdate(BaseModel):
    """What an estate administrator may change. The name is not editable."""

    description: str | None = Field(default=None, max_length=5000)
    is_public: bool | None = None
    show_living_score: bool | None = None

    model_config = ConfigDict(extra="forbid")


class EstatePhotoResponse(BaseModel):
    """One photo of the estate, as its administrator manages it."""

    photo_id: int
    public_id: str
    content_type: str
    width: int
    height: int
    bytes: int
    caption: str | None
    position: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EstatePhotoUpdate(BaseModel):
    """Reorder or re-caption one photo. The image itself is never replaced."""

    caption: str | None = Field(default=None, max_length=PHOTO_CAPTION_MAX_LENGTH)
    position: int | None = Field(default=None, ge=0, le=1000)

    model_config = ConfigDict(extra="forbid")
