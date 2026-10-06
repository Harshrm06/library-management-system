"""Comprehensive test suite for the Return Book + Fine Calculation system."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User, UserRole
from app.utils.jwt_utils import create_access_token


def _create_user(db, email="returner@example.com", role=UserRole.MEMBER):
    """Helper to create and persist a user."""
    user = User(
        email=email,
        password_hash="hashed_pw_123",
        first_name="Return",
        last_name="User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_book(db, title="Refactoring", total=5, available=3):
    """Helper to create and persist a book."""
    book = Book(
        title=title,
        author="Martin Fowler",
        isbn=f"978{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        total_quantity=total,
        available_quantity=available,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def _auth_header(user: User) -> dict:
    """Helper to construct JWT authorization header."""
    token = create_access_token(user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_return_book_success_on_time(client, db_session):
    """Verify returning a book on time succeeds without fine and increments stock."""
    user = _create_user(db_session, "ontime@example.com")
    book = _create_book(db_session, "Clean Architecture", total=5, available=2)
    headers = _auth_header(user)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now - timedelta(days=5),
        due_date=now + timedelta(days=9),
        return_date=None,
        status=BorrowingStatus.BORROWED,
        fine_amount=Decimal("0.00"),
    )
    db_session.add(record)
    db_session.commit()

    response = client.post(f"/api/return/{record.id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == record.id
    assert data["book_id"] == book.id
    assert data["status"] == "RETURNED"
    assert data["return_date"] is not None
    assert Decimal(str(data["fine_amount"])) == Decimal("0.00")
    assert data["remaining_available_quantity"] == 3
    assert data["message"] == "Book returned successfully"

    # Database state verification
    db_session.refresh(book)
    db_session.refresh(record)
    assert book.available_quantity == 3
    assert record.status == BorrowingStatus.RETURNED
    assert record.return_date is not None
    assert record.fine_amount == Decimal("0.00")


def test_return_book_success_late_fine_calculation(client, db_session):
    """Verify returning a late book calculates fine based on daily_fine_rate and overdue days."""
    user = _create_user(db_session, "late@example.com")
    book = _create_book(db_session, "Domain-Driven Design", total=5, available=1)
    headers = _auth_header(user)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # 3 days overdue
    due_date = now - timedelta(days=3)
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=due_date - timedelta(days=14),
        due_date=due_date,
        return_date=None,
        status=BorrowingStatus.BORROWED,
        fine_amount=Decimal("0.00"),
    )
    db_session.add(record)
    db_session.commit()

    response = client.post(f"/api/return/{record.id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RETURNED"
    expected_fine = Decimal("3.00") * settings.daily_fine_rate_decimal
    assert Decimal(str(data["fine_amount"])) == expected_fine
    assert data["remaining_available_quantity"] == 2

    db_session.refresh(record)
    assert record.fine_amount == expected_fine


def test_return_book_on_due_date(client, db_session):
    """Verify returning a book exactly on its due date incurs no fine."""
    user = _create_user(db_session, "exact@example.com")
    book = _create_book(db_session, "Design Patterns", total=5, available=2)
    headers = _auth_header(user)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now - timedelta(days=14),
        due_date=now + timedelta(hours=1),
        return_date=None,
        status=BorrowingStatus.BORROWED,
        fine_amount=Decimal("0.00"),
    )
    db_session.add(record)
    db_session.commit()

    response = client.post(f"/api/return/{record.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert Decimal(str(data["fine_amount"])) == Decimal("0.00")


def test_return_book_already_returned(client, db_session):
    """Verify attempting to return an already returned book is rejected."""
    user = _create_user(db_session, "already@example.com")
    book = _create_book(db_session, "Already Returned Book", total=5, available=3)
    headers = _auth_header(user)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now - timedelta(days=10),
        due_date=now + timedelta(days=4),
        return_date=now - timedelta(days=1),
        status=BorrowingStatus.RETURNED,
        fine_amount=Decimal("0.00"),
    )
    db_session.add(record)
    db_session.commit()

    response = client.post(f"/api/return/{record.id}", headers=headers)

    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "already_returned"

    # Verify inventory was NOT incremented again
    db_session.refresh(book)
    assert book.available_quantity == 3


def test_return_another_user_book(client, db_session):
    """Verify a user cannot return another user's borrowing record."""
    user_a = _create_user(db_session, "usera@example.com")
    user_b = _create_user(db_session, "userb@example.com")
    book = _create_book(db_session, "Shared Catalog Book", total=5, available=2)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record = BorrowingRecord(
        user_id=user_a.id,
        book_id=book.id,
        issue_date=now - timedelta(days=5),
        due_date=now + timedelta(days=9),
        return_date=None,
        status=BorrowingStatus.BORROWED,
        fine_amount=Decimal("0.00"),
    )
    db_session.add(record)
    db_session.commit()

    # User B attempts to return User A's record
    headers_b = _auth_header(user_b)
    response = client.post(f"/api/return/{record.id}", headers=headers_b)

    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "unauthorized_return"

    # Verify record and book stock remain unchanged
    db_session.refresh(record)
    db_session.refresh(book)
    assert record.status == BorrowingStatus.BORROWED
    assert record.return_date is None
    assert book.available_quantity == 2


def test_return_book_not_found(client, db_session):
    """Verify 404 response for non-existent borrowing record."""
    user = _create_user(db_session, "notfound_return@example.com")
    headers = _auth_header(user)

    response = client.post("/api/return/999999", headers=headers)

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "record_not_found"


def test_return_book_unauthenticated(client, db_session):
    """Verify 401 response when returning without authorization header."""
    user = _create_user(db_session, "unauth_return@example.com")
    book = _create_book(db_session, "Unauth Book", total=5, available=2)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now - timedelta(days=2),
        due_date=now + timedelta(days=12),
        status=BorrowingStatus.BORROWED,
    )
    db_session.add(record)
    db_session.commit()

    response = client.post(f"/api/return/{record.id}")

    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "missing_token"

    db_session.refresh(record)
    assert record.status == BorrowingStatus.BORROWED


def test_return_inventory_overflow_prevented(client, db_session):
    """Verify returning fails safely if available_quantity would exceed total_quantity."""
    user = _create_user(db_session, "overflow@example.com")
    # Inconsistent state: available_quantity equals total_quantity before return
    book = _create_book(db_session, "Corrupted Stock Book", total=5, available=5)
    headers = _auth_header(user)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now - timedelta(days=2),
        due_date=now + timedelta(days=12),
        status=BorrowingStatus.BORROWED,
    )
    db_session.add(record)
    db_session.commit()

    response = client.post(f"/api/return/{record.id}", headers=headers)

    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "inventory_overflow"

    db_session.refresh(book)
    db_session.refresh(record)
    assert book.available_quantity == 5
    assert record.status == BorrowingStatus.BORROWED


def test_concurrent_return_safety():
    """Verify concurrent return requests on the same borrowing record execute safely."""
    engine = create_engine("sqlite:///test_concurrency_return.db", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    session1 = Session()
    user = User(email="concur_return@example.com", password_hash="pw", first_name="U", last_name="L")
    book = Book(title="Concurrent Return Book", author="Author", isbn="9788888888888", total_quantity=5, available_quantity=2)
    session1.add_all([user, book])
    session1.commit()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now - timedelta(days=5),
        due_date=now + timedelta(days=9),
        status=BorrowingStatus.BORROWED,
    )
    session1.add(record)
    session1.commit()

    u_id, r_id, b_id = user.id, record.id, book.id
    session1.close()

    results = []

    def _return_worker():
        sess = Session()
        try:
            from app.controllers.borrow_controller import return_book
            u = sess.get(User, u_id)
            res = return_book(sess, u, r_id)
            results.append(("SUCCESS", res))
        except Exception as exc:
            results.append(("ERROR", str(exc)))
        finally:
            sess.close()

    t1 = threading.Thread(target=_return_worker)
    t2 = threading.Thread(target=_return_worker)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Cleanup DB file
    Base.metadata.drop_all(engine)
    engine.dispose()
    import os
    if os.path.exists("test_concurrency_return.db"):
        os.remove("test_concurrency_return.db")

    successes = [r for r in results if r[0] == "SUCCESS"]
    errors = [r for r in results if r[0] == "ERROR"]

    # Exactly 1 request succeeds and 1 fails
    assert len(successes) == 1
    assert len(errors) == 1
