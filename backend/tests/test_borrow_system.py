"""Comprehensive test suite for the Borrow Book System business logic and endpoints."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import threading
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User, UserRole
from app.utils.jwt_utils import create_access_token


def _create_user(db, email="member@example.com", role=UserRole.MEMBER):
    """Helper to persist a user."""
    user = User(
        email=email,
        password_hash="hashed_pw_123",
        first_name="Member",
        last_name="User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_book(db, title="Test Driven Development", available=2, total=5):
    """Helper to persist a book."""
    book = Book(
        title=title,
        author="Kent Beck",
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


def test_borrow_book_success(client, db_session):
    """Verify successful borrowing decrements stock and creates record."""
    user = _create_user(db_session, "success@example.com")
    book = _create_book(db_session, "Clean Code", available=3, total=5)
    headers = _auth_header(user)

    response = client.post(f"/api/borrow/{book.id}", headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["book_id"] == book.id
    assert data["book_title"] == "Clean Code"
    assert data["status"] == "BORROWED"
    assert data["return_date"] is None
    assert data["remaining_available_quantity"] == 2
    assert data["message"] == "Book borrowed successfully"

    # Database state verification
    db_session.refresh(book)
    assert book.available_quantity == 2

    records = db_session.query(BorrowingRecord).filter_by(user_id=user.id, book_id=book.id).all()
    assert len(records) == 1
    assert records[0].status == BorrowingStatus.BORROWED
    assert records[0].fine_amount == Decimal("0.00")
    assert records[0].return_date is None


def test_borrow_book_not_found(client, db_session):
    """Verify 404 response when borrowing non-existent book."""
    user = _create_user(db_session, "notfound@example.com")
    headers = _auth_header(user)

    response = client.post("/api/borrow/999999", headers=headers)

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "book_not_found"
    assert data["detail"] == "Book not found"

    records = db_session.query(BorrowingRecord).all()
    assert len(records) == 0


def test_borrow_book_unavailable(client, db_session):
    """Verify rejection when no available copies remain."""
    user = _create_user(db_session, "unavailable@example.com")
    book = _create_book(db_session, "Out of Stock Book", available=0, total=2)
    headers = _auth_header(user)

    response = client.post(f"/api/borrow/{book.id}", headers=headers)

    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "book_unavailable"

    db_session.refresh(book)
    assert book.available_quantity == 0

    records = db_session.query(BorrowingRecord).all()
    assert len(records) == 0


def test_borrow_book_duplicate_active(client, db_session):
    """Verify active borrowing prevents duplicate borrow requests."""
    user = _create_user(db_session, "duplicate@example.com")
    book = _create_book(db_session, "Popular Book", available=3, total=5)
    headers = _auth_header(user)

    # First borrowing succeeds
    res1 = client.post(f"/api/borrow/{book.id}", headers=headers)
    assert res1.status_code == 201

    # Second borrowing fails with 409 Conflict
    res2 = client.post(f"/api/borrow/{book.id}", headers=headers)
    assert res2.status_code == 409
    data = res2.json()
    assert data["code"] == "already_borrowed"

    # Stock should only have decremented once
    db_session.refresh(book)
    assert book.available_quantity == 2

    records = db_session.query(BorrowingRecord).filter_by(user_id=user.id, book_id=book.id).all()
    assert len(records) == 1


def test_borrow_after_previous_return(client, db_session):
    """Verify user can borrow the same book again after returning it."""
    user = _create_user(db_session, "returner@example.com")
    book = _create_book(db_session, "Reusable Book", available=2, total=5)
    headers = _auth_header(user)

    # Create an old RETURNED record
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    old_record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now - timedelta(days=20),
        due_date=now - timedelta(days=6),
        return_date=now - timedelta(days=5),
        status=BorrowingStatus.RETURNED,
        fine_amount=Decimal("0.00"),
    )
    db_session.add(old_record)
    db_session.commit()

    # Attempt borrowing again
    response = client.post(f"/api/borrow/{book.id}", headers=headers)
    assert response.status_code == 201

    db_session.refresh(book)
    assert book.available_quantity == 1

    records = db_session.query(BorrowingRecord).filter_by(user_id=user.id, book_id=book.id).all()
    assert len(records) == 2


def test_borrow_book_unauthenticated(client, db_session):
    """Verify unauthenticated requests are rejected with 401."""
    book = _create_book(db_session, "Protected Book", available=2, total=5)

    response = client.post(f"/api/borrow/{book.id}")
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "missing_token"

    db_session.refresh(book)
    assert book.available_quantity == 2

    records = db_session.query(BorrowingRecord).all()
    assert len(records) == 0


def test_transaction_rollback_on_failure(client, db_session):
    """Verify failure inside transaction rolls back inventory modification."""
    user = _create_user(db_session, "rollback@example.com")
    book = _create_book(db_session, "Rollback Book", available=2, total=5)
    headers = _auth_header(user)

    # Patch db.add to simulate failure after inventory decrement
    with patch.object(db_session, "add", side_effect=RuntimeError("Simulated database failure")):
        with pytest.raises(RuntimeError):
            client.post(f"/api/borrow/{book.id}", headers=headers)

    # Verify inventory was restored
    db_session.refresh(book)
    assert book.available_quantity == 2

    records = db_session.query(BorrowingRecord).all()
    assert len(records) == 0


def test_concurrent_borrowing_safety():
    """Verify concurrent requests for the last available copy resolve safely."""
    # Use disk-based SQLite file for multi-connection concurrency test
    engine = create_engine("sqlite:///test_concurrency.db", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    session1 = Session()
    u1 = User(email="user1@concur.com", password_hash="pw", first_name="U1", last_name="L1")
    u2 = User(email="user2@concur.com", password_hash="pw", first_name="U2", last_name="L2")
    book = Book(title="Last Copy", author="Author", isbn="9789999999999", total_quantity=1, available_quantity=1)
    session1.add_all([u1, u2, book])
    session1.commit()

    u1_id, u2_id, book_id = u1.id, u2.id, book.id
    session1.close()

    results = []

    def _borrow_worker(user_id):
        sess = Session()
        try:
            from app.controllers.borrow_controller import borrow_book
            u = sess.get(User, user_id)
            res = borrow_book(sess, u, book_id)
            results.append(("SUCCESS", user_id, res))
        except Exception as exc:
            results.append(("ERROR", user_id, str(exc)))
        finally:
            sess.close()

    t1 = threading.Thread(target=_borrow_worker, args=(u1_id,))
    t2 = threading.Thread(target=_borrow_worker, args=(u2_id,))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Cleanup test DB file
    Base.metadata.drop_all(engine)
    engine.dispose()
    import os
    if os.path.exists("test_concurrency.db"):
        os.remove("test_concurrency.db")

    successes = [r for r in results if r[0] == "SUCCESS"]
    errors = [r for r in results if r[0] == "ERROR"]

    # Exactly 1 request succeeds and 1 fails
    assert len(successes) == 1
    assert len(errors) == 1
