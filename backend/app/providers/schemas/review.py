from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    review_id: int = Field(..., serialization_alias="id")
    user_id: int
    provider_id: int
    rating: int
    comment: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True, "populate_by_name": True}


class PaginatedReviewsResponse(BaseModel):
    count: int
    reviews: list[ReviewResponse]
