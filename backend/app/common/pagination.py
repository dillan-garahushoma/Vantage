from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Common query parameters for paginated endpoints."""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed).")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of results per page.")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size
