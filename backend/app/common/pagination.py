from dataclasses import dataclass
from math import ceil
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, model_validator


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int = 0

    model_config = {"populate_by_name": True, "serialize_by_alias": True}

    @model_validator(mode="before")
    @classmethod
    def calculate_pages(cls, values: object) -> object:
        if isinstance(values, dict) and "pages" not in values:
            total = values["total"]
            size = values["size"]
            values["pages"] = ceil(total / size) if total else 0
        return values


@dataclass(frozen=True)
class PaginationParams:
    """Validated 1-based pagination options shared by collection endpoints."""

    page: int = Query(default=1, ge=1, description="1-based page number.")
    size: int = Query(default=20, ge=1, le=100, description="Items per page.")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size
