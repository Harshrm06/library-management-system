"""Request and response schemas for borrowing records, admin history, and dashboard statistics."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.borrowing_record import BorrowingStatus


class BorrowingRecordSchema(BaseModel):
    """Response representation of a borrowing record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    book_id: int
    issue_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    status: BorrowingStatus
    fine_amount: Decimal = Field(default=Decimal("0.00"))
    created_at: datetime
    updated_at: datetime


class BorrowResponseSchema(BaseModel):
    """Response returned upon successfully borrowing a book."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Borrowing record ID")
    book_id: int
    book_title: str
    issue_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    status: BorrowingStatus
    fine_amount: Decimal = Field(default=Decimal("0.00"))
    remaining_available_quantity: int = Field(description="Remaining available copies of the book")
    message: str = "Book borrowed successfully"


class ReturnResponseSchema(BorrowResponseSchema):
    """Response returned upon successfully returning a book."""

    message: str = "Book returned successfully"


class BorrowingBookSummary(BaseModel):
    """Minimal book details embedded in borrowing history responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    genre: Optional[str] = None


class BorrowingHistoryItem(BorrowingRecordSchema):
    """Borrowing record augmented with essential book information."""

    book: BorrowingBookSummary


class BorrowingHistoryResponse(BaseModel):
    """Paginated or list payload for user borrowing history."""

    model_config = ConfigDict(from_attributes=True)

    items: List[BorrowingHistoryItem]
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Items per page")
    total: int = Field(description="Total count of matching records")


class BorrowingMemberSummary(BaseModel):
    """Member summary embedded in admin borrowing history responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str
    last_name: str

    @computed_field
    @property
    def name(self) -> str:
        """Return full member name."""
        return f"{self.first_name} {self.last_name}".strip()


class AdminBorrowingHistoryItem(BorrowingRecordSchema):
    """Borrowing record augmented with book and member information for admin display."""

    book: BorrowingBookSummary
    user: BorrowingMemberSummary

    @computed_field
    @property
    def member(self) -> BorrowingMemberSummary:
        """Alias returning member summary."""
        return self.user


class AdminBorrowingHistoryResponse(BaseModel):
    """Paginated response payload for administrative borrowing history."""

    model_config = ConfigDict(from_attributes=True)

    items: List[AdminBorrowingHistoryItem]
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Items per page")
    total: int = Field(description="Total count of matching records")


class DashboardStatisticsSchema(BaseModel):
    """Dashboard statistics metrics schema for administrative monitoring."""

    model_config = ConfigDict(from_attributes=True)

    total_books: int = Field(default=0, description="Total unique book titles in catalog")
    available_books: int = Field(default=0, description="Book titles with available_quantity > 0")
    borrowed_books: int = Field(default=0, description="Active borrowing transactions (status BORROWED, return_date NULL)")
    overdue_books: int = Field(default=0, description="Active past-due borrowing transactions")
    total_members: int = Field(default=0, description="Total registered members (role MEMBER)")
    total_copies: int = Field(default=0, description="Total physical book copies in inventory")
    available_copies: int = Field(default=0, description="Total available physical book copies")
    total_users: int = Field(default=0, description="Total registered users")
    total_borrowed: int = Field(default=0, description="Active borrowing transactions")
    total_overdue: int = Field(default=0, description="Overdue borrowing transactions")
    total_returned: int = Field(default=0, description="Completed returned transactions")
    total_fines: Decimal = Field(default=Decimal("0.00"), description="Total accumulated fines")
