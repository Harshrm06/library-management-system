"""Comprehensive test suite for the Admin Borrowing History API."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User, UserRole
from app.utils.jwt_utils import create_access_token


def _create_user(db, email="admin_bh@example.com", role=UserRole.ADMIN, first_name="Admin", last_name="User"):
    """Helper to create and persist a user."""
    user = User(
        email=email,
        password_hash="hashed_pw_secret_123",
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_book(db, title="Clean Code", author="Robert C. Martin", isbn="9780132350884"):
    """Helper to create and persist a book."""
    book = Book(
        title=title,
        author=author,
        isbn=isbn,
        genre="Software",
        total_quantity=5,
        available_quantity=5,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def _create_record(db, user_id, book_id, status=BorrowingStatus.BORROWED, days_ago=5, is_returned=False):
    """Helper to create and persist a borrowing record."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    issue_date = now - timedelta(days=days_ago)
    due_date = issue_date + timedelta(days=14)
    return_date = (issue_date + timedelta(days=7)) if is_returned else None

    record = BorrowingRecord(
        user_id=user_id,
        book_id=book_id,
        issue_date=issue_date,
        due_date=due_date,
        return_date=return_date,
        status=status,
        fine_amount=Decimal("0.00"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _auth_header(user: User) -> dict:
    """Helper to construct JWT authorization header."""
    token = create_access_token(user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------

def test_admin_borrowing_history_authorization(client, db_session):
    """Verify ADMIN receives 200, MEMBER receives 403, unauthenticated receives 401."""
    admin = _create_user(db_session, "admin_auth_bh@example.com", role=UserRole.ADMIN)
    member = _create_user(db_session, "member_auth_bh@example.com", role=UserRole.MEMBER)

    # 1. Admin access succeeds
    res_admin = client.get("/api/admin/borrowings", headers=_auth_header(admin))
    assert res_admin.status_code == 200

    # 2. Member access rejected (403)
    res_member = client.get("/api/admin/borrowings", headers=_auth_header(member))
    assert res_member.status_code == 403
    assert res_member.json()["code"] == "permission_denied"

    # 3. Unauthenticated access rejected (401)
    res_unauth = client.get("/api/admin/borrowings")
    assert res_unauth.status_code == 401
    assert res_unauth.json()["code"] == "missing_token"


# ---------------------------------------------------------------------------
# Data Retrieval & Cross-Member Isolation Tests
# ---------------------------------------------------------------------------

def test_admin_sees_all_members_borrowing_records(client, db_session):
    """Verify admin can view borrowing records across multiple members."""
    admin = _create_user(db_session, "admin_cross@example.com", role=UserRole.ADMIN)
    m1 = _create_user(db_session, "m1_cross@example.com", role=UserRole.MEMBER, first_name="Member1")
    m2 = _create_user(db_session, "m2_cross@example.com", role=UserRole.MEMBER, first_name="Member2")

    b1 = _create_book(db_session, title="Book 1", isbn="9780000000101")
    b2 = _create_book(db_session, title="Book 2", isbn="9780000000102")

    _create_record(db_session, m1.id, b1.id, days_ago=10)
    _create_record(db_session, m2.id, b2.id, days_ago=2)

    res = client.get("/api/admin/borrowings", headers=_auth_header(admin))
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Verify book and member details are embedded correctly
    user_emails = {item["user"]["email"] for item in data["items"]}
    assert "m1_cross@example.com" in user_emails
    assert "m2_cross@example.com" in user_emails

    book_titles = {item["book"]["title"] for item in data["items"]}
    assert "Book 1" in book_titles
    assert "Book 2" in book_titles

    # Verify password hashes are excluded
    for item in data["items"]:
        assert "password_hash" not in item["user"]
        assert "password" not in item["user"]


# ---------------------------------------------------------------------------
# Default Sorting & Pagination Tests
# ---------------------------------------------------------------------------

def test_admin_borrowings_sorting_and_pagination(client, db_session):
    """Verify default issue_date DESC sorting and pagination behavior."""
    admin = _create_user(db_session, "admin_sort_page@example.com", role=UserRole.ADMIN)
    m = _create_user(db_session, "m_sort@example.com", role=UserRole.MEMBER)
    b = _create_book(db_session, isbn="9780000000201")

    r1 = _create_record(db_session, m.id, b.id, days_ago=15)  # Oldest
    r2 = _create_record(db_session, m.id, b.id, days_ago=10)
    r3 = _create_record(db_session, m.id, b.id, days_ago=2)   # Newest

    headers = _auth_header(admin)

    # Default pagination (newest first: r3, r2, r1)
    res_p1 = client.get("/api/admin/borrowings?page=1&page_size=2", headers=headers)
    assert res_p1.status_code == 200
    d1 = res_p1.json()
    assert d1["total"] == 3
    assert len(d1["items"]) == 2
    assert d1["items"][0]["id"] == r3.id
    assert d1["items"][1]["id"] == r2.id

    # Page 2
    res_p2 = client.get("/api/admin/borrowings?page=2&page_size=2", headers=headers)
    assert res_p2.status_code == 200
    d2 = res_p2.json()
    assert d2["total"] == 3
    assert len(d2["items"]) == 1
    assert d2["items"][0]["id"] == r1.id


# ---------------------------------------------------------------------------
# Status Filter Tests
# ---------------------------------------------------------------------------

def test_admin_borrowings_status_filter(client, db_session):
    """Verify filtering by BORROWED and RETURNED statuses, and invalid status rejection."""
    admin = _create_user(db_session, "admin_status@example.com", role=UserRole.ADMIN)
    m = _create_user(db_session, "m_status@example.com", role=UserRole.MEMBER)
    b = _create_book(db_session, isbn="9780000000301")

    _create_record(db_session, m.id, b.id, status=BorrowingStatus.BORROWED, days_ago=5)
    _create_record(db_session, m.id, b.id, status=BorrowingStatus.RETURNED, days_ago=12, is_returned=True)

    headers = _auth_header(admin)

    # Filter BORROWED
    res_b = client.get("/api/admin/borrowings?status=BORROWED", headers=headers)
    assert res_b.status_code == 200
    assert res_b.json()["total"] == 1
    assert res_b.json()["items"][0]["status"] == "BORROWED"

    # Filter RETURNED
    res_r = client.get("/api/admin/borrowings?status=RETURNED", headers=headers)
    assert res_r.status_code == 200
    assert res_r.json()["total"] == 1
    assert res_r.json()["items"][0]["status"] == "RETURNED"

    # Invalid status
    res_inv = client.get("/api/admin/borrowings?status=INVALID_STATUS", headers=headers)
    assert res_inv.status_code == 422


# ---------------------------------------------------------------------------
# Search Tests
# ---------------------------------------------------------------------------

def test_admin_borrowings_search_filtering(client, db_session):
    """Verify search across member email, first_name, last_name, book title, author, and ISBN."""
    admin = _create_user(db_session, "admin_search_bh@example.com", role=UserRole.ADMIN)
    m1 = _create_user(db_session, "rahul.sharma@example.com", role=UserRole.MEMBER, first_name="Rahul", last_name="Sharma")
    m2 = _create_user(db_session, "priya.verma@example.com", role=UserRole.MEMBER, first_name="Priya", last_name="Verma")

    b1 = _create_book(db_session, title="Clean Architecture", author="Robert Martin", isbn="9780134494166")
    b2 = _create_book(db_session, title="Design Patterns", author="Erich Gamma", isbn="9780201633610")

    _create_record(db_session, m1.id, b1.id, days_ago=4)
    _create_record(db_session, m2.id, b2.id, days_ago=3)

    headers = _auth_header(admin)

    # Search member first name
    res_m = client.get("/api/admin/borrowings?search=rahul", headers=headers)
    assert res_m.status_code == 200
    assert res_m.json()["total"] == 1
    assert res_m.json()["items"][0]["user"]["email"] == "rahul.sharma@example.com"

    # Search book title
    res_t = client.get("/api/admin/borrowings?search=Architecture", headers=headers)
    assert res_t.status_code == 200
    assert res_t.json()["total"] == 1
    assert res_t.json()["items"][0]["book"]["title"] == "Clean Architecture"

    # Search book ISBN
    res_isbn = client.get("/api/admin/borrowings?search=9780201633610", headers=headers)
    assert res_isbn.status_code == 200
    assert res_isbn.json()["total"] == 1
    assert res_isbn.json()["items"][0]["book"]["title"] == "Design Patterns"


# ---------------------------------------------------------------------------
# Date Range & Member Filter Tests
# ---------------------------------------------------------------------------

def test_admin_borrowings_date_and_user_filters(client, db_session):
    """Verify from_date, to_date, and user_id filtering."""
    admin = _create_user(db_session, "admin_dt_filt@example.com", role=UserRole.ADMIN)
    m1 = _create_user(db_session, "m1_dt@example.com", role=UserRole.MEMBER)
    m2 = _create_user(db_session, "m2_dt@example.com", role=UserRole.MEMBER)
    b = _create_book(db_session, isbn="9780000000401")

    r1 = _create_record(db_session, m1.id, b.id, days_ago=20)
    r2 = _create_record(db_session, m2.id, b.id, days_ago=5)

    headers = _auth_header(admin)

    # Filter user_id=m1.id
    res_usr = client.get(f"/api/admin/borrowings?user_id={m1.id}", headers=headers)
    assert res_usr.status_code == 200
    assert res_usr.json()["total"] == 1
    assert res_usr.json()["items"][0]["id"] == r1.id

    # Date filter matching r2 (5 days ago)
    now = datetime.now(timezone.utc).date()
    from_str = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    to_str = now.strftime("%Y-%m-%d")

    res_dt = client.get(f"/api/admin/borrowings?from_date={from_str}&to_date={to_str}", headers=headers)
    assert res_dt.status_code == 200
    assert res_dt.json()["total"] == 1
    assert res_dt.json()["items"][0]["id"] == r2.id

    # Invalid date range (from_date > to_date)
    res_inv_dt = client.get(f"/api/admin/borrowings?from_date={to_str}&to_date={from_str}", headers=headers)
    assert res_inv_dt.status_code == 400
    assert res_inv_dt.json()["code"] == "invalid_date_range"


# ---------------------------------------------------------------------------
# Empty Results Test
# ---------------------------------------------------------------------------

def test_admin_borrowings_empty_result(client, db_session):
    """Verify a filter matching nothing returns 200 with items=[] and total=0."""
    admin = _create_user(db_session, "admin_empty_bh@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    res = client.get("/api/admin/borrowings?search=NONEXISTENT_QUERY", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0
