"""Comprehensive test suite for the Admin Dashboard Statistics API."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User, UserRole
from app.utils.jwt_utils import create_access_token


def _create_user(db, email="admin_test@example.com", role=UserRole.MEMBER):
    """Helper to create and persist a user with a given role."""
    user = User(
        email=email,
        password_hash="hashed_pw_123",
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_book(db, title="Stats Book", total=5, available=3):
    """Helper to create and persist a book."""
    book = Book(
        title=title,
        author="Stats Author",
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


def test_admin_access_success(client, db_session):
    """Verify an ADMIN user can successfully access dashboard stats."""
    admin = _create_user(db_session, "admin1@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    response = client.get("/api/admin/dashboard/stats", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "total_books" in data
    assert "available_books" in data
    assert "borrowed_books" in data
    assert "overdue_books" in data
    assert "total_members" in data


def test_member_access_rejected(client, db_session):
    """Verify a MEMBER user cannot access dashboard stats (HTTP 403)."""
    member = _create_user(db_session, "member1@example.com", role=UserRole.MEMBER)
    headers = _auth_header(member)

    response = client.get("/api/admin/dashboard/stats", headers=headers)

    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "permission_denied"


def test_unauthenticated_access_rejected(client):
    """Verify request without JWT token is rejected (HTTP 401)."""
    response = client.get("/api/admin/dashboard/stats")

    assert response.status_code == 401
    assert response.json()["code"] == "missing_token"


def test_correct_total_books_counts_rows_not_copies(client, db_session):
    """Verify total_books counts Book rows rather than physical copy quantities."""
    admin = _create_user(db_session, "admin_books@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    # 3 Book rows, each with total_quantity = 10
    _create_book(db_session, "Book A", total=10, available=10)
    _create_book(db_session, "Book B", total=10, available=10)
    _create_book(db_session, "Book C", total=10, available=10)

    response = client.get("/api/admin/dashboard/stats", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total_books"] == 3
    assert data["total_copies"] == 30


def test_available_books_semantics(client, db_session):
    """Verify available_books counts titles with available_quantity > 0."""
    admin = _create_user(db_session, "admin_avail@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    _create_book(db_session, "Available Title 1", total=5, available=2)
    _create_book(db_session, "Available Title 2", total=5, available=5)
    _create_book(db_session, "Unavailable Title", total=5, available=0)

    response = client.get("/api/admin/dashboard/stats", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total_books"] == 3
    assert data["available_books"] == 2


def test_borrowed_books_counts_active_only(client, db_session):
    """Verify borrowed_books counts only active BORROWED records (return_date NULL)."""
    admin = _create_user(db_session, "admin_borrowed@example.com", role=UserRole.ADMIN)
    member = _create_user(db_session, "member_borrowed@example.com", role=UserRole.MEMBER)
    book = _create_book(db_session, "Borrowed Book")
    headers = _auth_header(admin)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Active borrowing
    rec1 = BorrowingRecord(
        user_id=member.id,
        book_id=book.id,
        issue_date=now - timedelta(days=2),
        due_date=now + timedelta(days=12),
        return_date=None,
        status=BorrowingStatus.BORROWED,
    )
    # Returned borrowing
    rec2 = BorrowingRecord(
        user_id=member.id,
        book_id=book.id,
        issue_date=now - timedelta(days=20),
        due_date=now - timedelta(days=6),
        return_date=now - timedelta(days=5),
        status=BorrowingStatus.RETURNED,
    )
    db_session.add_all([rec1, rec2])
    db_session.commit()

    response = client.get("/api/admin/dashboard/stats", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["borrowed_books"] == 1


def test_overdue_books_identifies_active_past_due(client, db_session):
    """Verify overdue_books identifies active past-due records and excludes returned ones."""
    admin = _create_user(db_session, "admin_overdue@example.com", role=UserRole.ADMIN)
    member = _create_user(db_session, "member_overdue@example.com", role=UserRole.MEMBER)
    book = _create_book(db_session, "Overdue Test Book")
    headers = _auth_header(admin)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Active, on time
    rec_on_time = BorrowingRecord(
        user_id=member.id,
        book_id=book.id,
        issue_date=now - timedelta(days=2),
        due_date=now + timedelta(days=12),
        return_date=None,
        status=BorrowingStatus.BORROWED,
    )
    # Active, overdue (due_date in past, return_date NULL)
    rec_overdue = BorrowingRecord(
        user_id=member.id,
        book_id=book.id,
        issue_date=now - timedelta(days=20),
        due_date=now - timedelta(days=6),
        return_date=None,
        status=BorrowingStatus.BORROWED,
    )
    # Returned, was overdue when returned
    rec_returned_late = BorrowingRecord(
        user_id=member.id,
        book_id=book.id,
        issue_date=now - timedelta(days=25),
        due_date=now - timedelta(days=11),
        return_date=now - timedelta(days=2),
        status=BorrowingStatus.RETURNED,
        fine_amount=Decimal("9.00"),
    )
    db_session.add_all([rec_on_time, rec_overdue, rec_returned_late])
    db_session.commit()

    response = client.get("/api/admin/dashboard/stats", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["borrowed_books"] == 2
    assert data["overdue_books"] == 1


def test_total_members_counts_only_member_role(client, db_session):
    """Verify total_members counts users with MEMBER role and excludes ADMIN users."""
    admin = _create_user(db_session, "admin_members@example.com", role=UserRole.ADMIN)
    _create_user(db_session, "admin2@example.com", role=UserRole.ADMIN)
    _create_user(db_session, "member_a@example.com", role=UserRole.MEMBER)
    _create_user(db_session, "member_b@example.com", role=UserRole.MEMBER)
    _create_user(db_session, "member_c@example.com", role=UserRole.MEMBER)
    headers = _auth_header(admin)

    response = client.get("/api/admin/dashboard/stats", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total_members"] == 3
    assert data["total_users"] == 5


def test_combined_realistic_statistics(client, db_session):
    """Verify all 5 dashboard statistics together in a realistic dataset."""
    admin = _create_user(db_session, "admin_combined@example.com", role=UserRole.ADMIN)
    m1 = _create_user(db_session, "comb_m1@example.com", role=UserRole.MEMBER)
    m2 = _create_user(db_session, "comb_m2@example.com", role=UserRole.MEMBER)

    b1 = _create_book(db_session, "Book 1", total=3, available=2)
    b2 = _create_book(db_session, "Book 2", total=2, available=0)
    b3 = _create_book(db_session, "Book 3", total=4, available=4)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # m1 borrows b1 active on-time
    rec1 = BorrowingRecord(
        user_id=m1.id,
        book_id=b1.id,
        issue_date=now - timedelta(days=1),
        due_date=now + timedelta(days=13),
        return_date=None,
        status=BorrowingStatus.BORROWED,
    )
    # m2 borrows b2 active overdue
    rec2 = BorrowingRecord(
        user_id=m2.id,
        book_id=b2.id,
        issue_date=now - timedelta(days=18),
        due_date=now - timedelta(days=4),
        return_date=None,
        status=BorrowingStatus.BORROWED,
    )
    db_session.add_all([rec1, rec2])
    db_session.commit()

    headers = _auth_header(admin)
    response = client.get("/api/admin/dashboard/stats", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total_books"] == 3
    assert data["available_books"] == 2
    assert data["borrowed_books"] == 2
    assert data["overdue_books"] == 1
    assert data["total_members"] == 2
