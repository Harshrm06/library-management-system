"""Book request and response schemas for admin inventory management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookBase(BaseModel):
    """Fields shared across book creation and representation."""

    title: str = Field(min_length=1, max_length=255, description="Book title")
    author: str = Field(min_length=1, max_length=255, description="Book author")
    isbn: str = Field(min_length=1, max_length=20, description="Unique ISBN-10 or ISBN-13")
    genre: Optional[str] = Field(default=None, max_length=100, description="Literary genre or category")
    description: Optional[str] = Field(default=None, description="Detailed book summary")
    published_year: Optional[int] = Field(default=None, ge=1000, le=2100, description="Publication year")


class BookCreate(BookBase):
    """Payload used to add a new book to the library inventory."""

    total_quantity: int = Field(default=1, ge=1, description="Total physical copies (must be >= 1)")
    available_quantity: Optional[int] = Field(default=None, ge=0, description="Initial available copies")

    @field_validator("available_quantity", mode="before")
    @classmethod
    def validate_available_quantity(cls, v: Any) -> Any:
        if v is not None:
            if isinstance(v, int) and v < 0:
                raise ValueError("available_quantity cannot be negative")
        return v


class BookUpdate(BaseModel):
    """Payload used by an admin to update book metadata and inventory levels."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    author: Optional[str] = Field(default=None, min_length=1, max_length=255)
    isbn: Optional[str] = Field(default=None, min_length=1, max_length=20)
    genre: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None)
    published_year: Optional[int] = Field(default=None, ge=1000, le=2100)
    total_quantity: Optional[int] = Field(default=None, ge=0)
    available_quantity: Optional[int] = Field(default=None, ge=0)


class BookOut(BookBase):
    """Public representation of a book including inventory status."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    total_quantity: int
    available_quantity: int
    is_available: bool
    created_at: datetime
    updated_at: datetime


class BookListResponse(BaseModel):
    """Paginated book listing response for administration."""

    model_config = ConfigDict(from_attributes=True)

    items: List[BookOut]
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Items per page")
    total: int = Field(description="Total count of matching book records")
