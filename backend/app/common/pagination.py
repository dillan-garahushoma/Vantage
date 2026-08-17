"""
Shared pagination utilities.
Provides a reusable query-parameter schema and a generic paginated response wrapper.
"""
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class PaginationParams:
    """
    FastAPI dependency for standard page/size query parameters.

    Usage::

        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends()):
            ...
    """

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
        size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    ):
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


class Page(BaseModel, Generic[T]):
    """Generic paginated response envelope."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: list[T], total: int, params: PaginationParams) -> "Page[T]":
        pages = max(1, -(-total // params.size))  # ceiling division
        return cls(items=items, total=total, page=params.page, size=params.size, pages=pages)
