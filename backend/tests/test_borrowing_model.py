"""Focused unit tests for BorrowingRecord model, relationships, and schema validations."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User, UserRole
from app.schemas.borrowing_schema import (
    BorrowingBookSummary,
    BorrowingHistoryItem,
    BorrowingHistoryResponse,
    BorrowingRecordSchema,
    DashboardStatisticsSchema,
)


def _utcnow() -> datetime:
    """Return naive UTC timestamp for SQLAlchemy compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def test_create_borrowing_record(db_session):
    """Verify BorrowingRecord can be created with valid data."""
    user = User(
        email="testuser@example.com",
        password_hash="hashed_pw",
        first_name="John",
        last_name="Doe",
        role=UserRole.MEMBER,
    )
    book = Book(
        title="Test Book",
        author="Author Name",
        isbn="1234567890123",
        total_quantity=5,
        available_quantity=5,
    )
    db_session.add_all([user, book])
    db_session.commit()

    now = _utcnow()
    due = now + timedelta(days=14)

    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now,
        due_date=due,
        status=BorrowingStatus.BORROWED,
    )
    db_session.add(record)
    db_session.commit()

    assert record.id is not None
    assert record.user_id == user.id
    assert record.book_id == book.id
    assert record.return_date is None
    assert record.fine_amount == Decimal("0.00")
    assert record.status == BorrowingStatus.BORROWED


def test_user_and_book_relationships(db_session):
    """Verify bidirectional User, Book, and BorrowingRecord relationships."""
    user = User(
        email="borrower@example.com",
        password_hash="hashed_pw",
        first_name="Jane",
        last_name="Smith",
    )
    book = Book(
        title="Python Guide",
        author="Guido",
        isbn="9780123456789",
    )
    db_session.add_all([user, book])
    db_session.commit()

    now = _utcnow()
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now,
        due_date=now + timedelta(days=7),
        status=BorrowingStatus.BORROWED,
    )
    db_session.add(record)
    db_session.commit()

    # Record -> User / Book relationships
    assert record.user.id == user.id
    assert record.user.email == "borrower@example.com"
    assert record.book.id == book.id
    assert record.book.title == "Python Guide"

    # User / Book -> Record relationships
    assert len(user.borrowing_records) == 1
    assert user.borrowing_records[0].id == record.id

    assert len(book.borrowing_records) == 1
    assert book.borrowing_records[0].id == record.id


def test_nullable_return_date(db_session):
    """Verify return_date can be null initially and populated upon return."""
    user = User(
        email="user2@example.com",
        password_hash="hashed",
        first_name="Alice",
        last_name="W",
    )
    book = Book(title="Book 2", author="Author 2", isbn="9781111111111")
    db_session.add_all([user, book])
    db_session.commit()

    now = _utcnow()
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now,
        due_date=now + timedelta(days=10),
        return_date=None,
        status=BorrowingStatus.BORROWED,
    )
    db_session.add(record)
    db_session.commit()

    assert record.return_date is None

    # Update return date
    returned_time = _utcnow()
    record.return_date = returned_time
    record.status = BorrowingStatus.RETURNED
    db_session.commit()

    assert record.return_date == returned_time
    assert record.status == BorrowingStatus.RETURNED


def test_status_enum_values(db_session):
    """Verify status accepts BORROWED, RETURNED, and OVERDUE."""
    user = User(
        email="user3@example.com",
        password_hash="hashed",
        first_name="Bob",
        last_name="M",
    )
    book = Book(title="Book 3", author="Author 3", isbn="9782222222222")
    db_session.add_all([user, book])
    db_session.commit()

    now = _utcnow()
    rec1 = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now,
        due_date=now + timedelta(days=5),
        status=BorrowingStatus.BORROWED,
    )
    rec2 = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now,
        due_date=now + timedelta(days=5),
        status=BorrowingStatus.RETURNED,
    )
    rec3 = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now,
        due_date=now + timedelta(days=5),
        status=BorrowingStatus.OVERDUE,
    )
    db_session.add_all([rec1, rec2, rec3])
    db_session.commit()

    assert rec1.status == BorrowingStatus.BORROWED
    assert rec2.status == BorrowingStatus.RETURNED
    assert rec3.status == BorrowingStatus.OVERDUE


def test_fine_amount_defaults(db_session):
    """Verify fine_amount defaults to 0.00 and can be updated."""
    user = User(
        email="user4@example.com",
        password_hash="hashed",
        first_name="Charlie",
        last_name="K",
    )
    book = Book(title="Book 4", author="Author 4", isbn="9783333333333")
    db_session.add_all([user, book])
    db_session.commit()

    now = _utcnow()
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now,
        due_date=now + timedelta(days=5),
    )
    db_session.add(record)
    db_session.commit()

    assert record.fine_amount == Decimal("0.00")

    # Update fine amount
    record.fine_amount = Decimal("15.50")
    db_session.commit()

    assert record.fine_amount == Decimal("15.50")


def test_existing_user_and_book_models_remain_functional(db_session):
    """Verify existing User and Book models remain fully functional."""
    user = User(
        email="user5@example.com",
        password_hash="hashed",
        first_name="Dave",
        last_name="L",
        role=UserRole.ADMIN,
    )
    book = Book(
        title="Book 5",
        author="Author 5",
        isbn="9784444444444",
        total_quantity=10,
        available_quantity=10,
    )
    db_session.add_all([user, book])
    db_session.commit()

    assert user.id is not None
    assert user.role == UserRole.ADMIN
    assert book.id is not None
    assert book.is_available is True
    assert len(user.borrowing_records) == 0
    assert len(book.borrowing_records) == 0


def test_pydantic_schemas(db_session):
    """Verify Pydantic schemas serialize model attributes correctly."""
    user = User(
        email="schema_user@example.com",
        password_hash="hashed",
        first_name="Schema",
        last_name="Tester",
    )
    book = Book(
        title="Schema Book",
        author="Schema Author",
        isbn="9785555555555",
        genre="Tech",
    )
    db_session.add_all([user, book])
    db_session.commit()

    now = _utcnow()
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now,
        due_date=now + timedelta(days=14),
        status=BorrowingStatus.BORROWED,
        fine_amount=Decimal("0.00"),
    )
    db_session.add(record)
    db_session.commit()

    # Validate BorrowingRecordSchema from ORM
    record_schema = BorrowingRecordSchema.model_validate(record)
    assert record_schema.id == record.id
    assert record_schema.user_id == user.id
    assert record_schema.book_id == book.id
    assert record_schema.status == BorrowingStatus.BORROWED

    # Validate BorrowingHistoryResponse with embedded book summary
    book_summary = BorrowingBookSummary.model_validate(book)
    history_item = BorrowingHistoryItem(
        **record_schema.model_dump(),
        book=book_summary,
    )
    history_resp = BorrowingHistoryResponse(items=[history_item], total=1)
    assert history_resp.total == 1
    assert history_resp.items[0].book.title == "Schema Book"

    # Validate DashboardStatisticsSchema
    stats = DashboardStatisticsSchema(
        total_books=10,
        total_copies=50,
        available_copies=40,
        total_users=20,
        total_borrowed=10,
        total_overdue=2,
        total_returned=30,
        total_fines=Decimal("25.00"),
    )
    assert stats.total_books == 10
    assert stats.total_overdue == 2
