"""Comprehensive test suite for the Member Borrowing History API."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User, UserRole
from app.utils.jwt_utils import create_access_token


def _create_user(db, email="history_user@example.com"):
    """Helper to create and persist a user."""
    user = User(
        email=email,
        password_hash="hashed_pw_123",
        first_name="History",
        last_name="Tester",
        role=UserRole.MEMBER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_book(db, title="History Book", author="Author Person"):
    """Helper to create and persist a book."""
    book = Book(
        title=title,
        author=author,
        isbn=f"978{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        total_quantity=5,
        available_quantity=5,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def _auth_header(user: User) -> dict:
    """Helper to construct JWT authorization header."""
    token = create_access_token(user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_get_history_authenticated_user(client, db_session):
    """Verify authenticated user can retrieve their borrowing history."""
    user = _create_user(db_session, "user1@example.com")
    book1 = _create_book(db_session, "Book One", "Author One")
    book2 = _create_book(db_session, "Book Two", "Author Two")
    headers = _auth_header(user)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rec1 = BorrowingRecord(
        user_id=user.id,
        book_id=book1.id,
        issue_date=now - timedelta(days=10),
        due_date=now + timedelta(days=4),
        status=BorrowingStatus.BORROWED,
    )
    rec2 = BorrowingRecord(
        user_id=user.id,
        book_id=book2.id,
        issue_date=now - timedelta(days=5),
        due_date=now + timedelta(days=9),
        status=BorrowingStatus.BORROWED,
    )
    db_session.add_all([rec1, rec2])
    db_session.commit()

    response = client.get("/api/borrow/history", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 10


def test_user_isolation(client, db_session):
    """Verify User A cannot see User B's borrowing history."""
    user_a = _create_user(db_session, "usera_hist@example.com")
    user_b = _create_user(db_session, "userb_hist@example.com")
    book = _create_book(db_session, "Isolated Book")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rec_a = BorrowingRecord(
        user_id=user_a.id,
        book_id=book.id,
        issue_date=now - timedelta(days=3),
        due_date=now + timedelta(days=11),
        status=BorrowingStatus.BORROWED,
    )
    rec_b = BorrowingRecord(
        user_id=user_b.id,
        book_id=book.id,
        issue_date=now - timedelta(days=1),
        due_date=now + timedelta(days=13),
        status=BorrowingStatus.BORROWED,
    )
    db_session.add_all([rec_a, rec_b])
    db_session.commit()

    # Authenticate as User A
    headers_a = _auth_header(user_a)
    res_a = client.get("/api/borrow/history", headers=headers_a)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["total"] == 1
    assert data_a["items"][0]["id"] == rec_a.id
    assert data_a["items"][0]["user_id"] == user_a.id

    # Authenticate as User B
    headers_b = _auth_header(user_b)
    res_b = client.get("/api/borrow/history", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["total"] == 1
    assert data_b["items"][0]["id"] == rec_b.id
    assert data_b["items"][0]["user_id"] == user_b.id


def test_empty_history(client, db_session):
    """Verify returning empty history for a user with no borrowing records."""
    user = _create_user(db_session, "empty_hist@example.com")
    headers = _auth_header(user)

    response = client.get("/api/borrow/history", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 10


def test_returned_and_active_records_both_appear(client, db_session):
    """Verify both BORROWED and RETURNED records appear in history."""
    user = _create_user(db_session, "both_types@example.com")
    book1 = _create_book(db_session, "Book Active")
    book2 = _create_book(db_session, "Book Returned")
    headers = _auth_header(user)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rec1 = BorrowingRecord(
        user_id=user.id,
        book_id=book1.id,
        issue_date=now - timedelta(days=2),
        due_date=now + timedelta(days=12),
        status=BorrowingStatus.BORROWED,
    )
    rec2 = BorrowingRecord(
        user_id=user.id,
        book_id=book2.id,
        issue_date=now - timedelta(days=15),
        due_date=now - timedelta(days=1),
        return_date=now - timedelta(days=1),
        status=BorrowingStatus.RETURNED,
    )
    db_session.add_all([rec1, rec2])
    db_session.commit()

    response = client.get("/api/borrow/history", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    statuses = {item["status"] for item in data["items"]}
    assert statuses == {"BORROWED", "RETURNED"}


def test_book_information_included(client, db_session):
    """Verify each history item includes embedded Book details."""
    user = _create_user(db_session, "book_details@example.com")
    book = _create_book(db_session, "Detailed Book Title", author="Famous Author")
    headers = _auth_header(user)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now,
        due_date=now + timedelta(days=14),
        status=BorrowingStatus.BORROWED,
    )
    db_session.add(record)
    db_session.commit()

    response = client.get("/api/borrow/history", headers=headers)

    assert response.status_code == 200
    data = response.json()
    item = data["items"][0]
    assert "book" in item
    assert item["book"]["id"] == book.id
    assert item["book"]["title"] == "Detailed Book Title"
    assert item["book"]["author"] == "Famous Author"
    assert item["book"]["isbn"] == book.isbn


def test_default_sorting_newest_first(client, db_session):
    """Verify default ordering is newest issue_date first."""
    user = _create_user(db_session, "sorting@example.com")
    book = _create_book(db_session, "Sorted Book")
    headers = _auth_header(user)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rec_old = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now - timedelta(days=30),
        due_date=now - timedelta(days=16),
        status=BorrowingStatus.RETURNED,
    )
    rec_new = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now - timedelta(days=2),
        due_date=now + timedelta(days=12),
        status=BorrowingStatus.BORROWED,
    )
    db_session.add_all([rec_old, rec_new])
    db_session.commit()

    response = client.get("/api/borrow/history", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["id"] == rec_new.id
    assert data["items"][1]["id"] == rec_old.id


def test_pagination(client, db_session):
    """Verify pagination across multiple pages."""
    user = _create_user(db_session, "paginate@example.com")
    book = _create_book(db_session, "Paginated Book")
    headers = _auth_header(user)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    records = []
    for i in range(15):
        rec = BorrowingRecord(
            user_id=user.id,
            book_id=book.id,
            issue_date=now - timedelta(days=i),
            due_date=now + timedelta(days=14 - i),
            status=BorrowingStatus.BORROWED,
        )
        records.append(rec)
    db_session.add_all(records)
    db_session.commit()

    # Page 1 (size 10)
    res_p1 = client.get("/api/borrow/history?page=1&page_size=10", headers=headers)
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert data_p1["total"] == 15
    assert len(data_p1["items"]) == 10
    p1_ids = [item["id"] for item in data_p1["items"]]

    # Page 2 (size 10)
    res_p2 = client.get("/api/borrow/history?page=2&page_size=10", headers=headers)
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert data_p2["total"] == 15
    assert len(data_p2["items"]) == 5
    p2_ids = [item["id"] for item in data_p2["items"]]

    # Verify no overlap between page 1 and page 2
    assert set(p1_ids).isdisjoint(set(p2_ids))
    assert len(set(p1_ids + p2_ids)) == 15


def test_status_filter(client, db_session):
    """Verify filtering history by status parameter."""
    user = _create_user(db_session, "filter@example.com")
    book = _create_book(db_session, "Filter Book")
    headers = _auth_header(user)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rec_borrowed = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now - timedelta(days=1),
        due_date=now + timedelta(days=13),
        status=BorrowingStatus.BORROWED,
    )
    rec_returned = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=now - timedelta(days=20),
        due_date=now - timedelta(days=6),
        return_date=now - timedelta(days=5),
        status=BorrowingStatus.RETURNED,
    )
    db_session.add_all([rec_borrowed, rec_returned])
    db_session.commit()

    # Filter BORROWED
    res_borrowed = client.get("/api/borrow/history?status=BORROWED", headers=headers)
    assert res_borrowed.status_code == 200
    data_b = res_borrowed.json()
    assert data_b["total"] == 1
    assert data_b["items"][0]["status"] == "BORROWED"

    # Filter RETURNED
    res_returned = client.get("/api/borrow/history?status=RETURNED", headers=headers)
    assert res_returned.status_code == 200
    data_r = res_returned.json()
    assert data_r["total"] == 1
    assert data_r["items"][0]["status"] == "RETURNED"


def test_invalid_status_filter(client, db_session):
    """Verify invalid status parameter produces validation error."""
    user = _create_user(db_session, "invalid_status@example.com")
    headers = _auth_header(user)

    response = client.get("/api/borrow/history?status=INVALID_STATUS", headers=headers)
    assert response.status_code == 422


def test_invalid_pagination_parameters(client, db_session):
    """Verify page < 1, page_size < 1, or page_size > 100 produce validation errors."""
    user = _create_user(db_session, "invalid_page@example.com")
    headers = _auth_header(user)

    # page = 0
    res1 = client.get("/api/borrow/history?page=0", headers=headers)
    assert res1.status_code == 422

    # page_size = 0
    res2 = client.get("/api/borrow/history?page_size=0", headers=headers)
    assert res2.status_code == 422

    # page_size > 100
    res3 = client.get("/api/borrow/history?page_size=101", headers=headers)
    assert res3.status_code == 422


def test_unauthenticated_request(client):
    """Verify request without JWT token is rejected with 401."""
    response = client.get("/api/borrow/history")
    assert response.status_code == 401
    assert response.json()["code"] == "missing_token"


def test_unexpected_user_id_query_param_ignored(client, db_session):
    """Verify passing user_id=other_id in query string does NOT compromise user isolation."""
    user_a = _create_user(db_session, "usera_hack@example.com")
    user_b = _create_user(db_session, "userb_hack@example.com")
    book = _create_book(db_session, "Secured Book")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rec_b = BorrowingRecord(
        user_id=user_b.id,
        book_id=book.id,
        issue_date=now,
        due_date=now + timedelta(days=14),
        status=BorrowingStatus.BORROWED,
    )
    db_session.add(rec_b)
    db_session.commit()

    # Authenticate as User A and attempt to query user_id=user_b.id
    headers_a = _auth_header(user_a)
    response = client.get(f"/api/borrow/history?user_id={user_b.id}", headers=headers_a)

    assert response.status_code == 200
    data = response.json()
    # Should return User A's empty history, NOT User B's record
    assert data["total"] == 0
    assert data["items"] == []
