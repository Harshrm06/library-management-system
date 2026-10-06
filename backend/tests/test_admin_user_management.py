"""Comprehensive test suite for the Admin User Management API."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User, UserRole
from app.utils.jwt_utils import create_access_token


def _create_user(db, email="user_mgmt@example.com", role=UserRole.MEMBER, first_name="John", last_name="Doe"):
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


def _auth_header(user: User) -> dict:
    """Helper to construct JWT authorization header."""
    token = create_access_token(user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_admin_list_users_success(client, db_session):
    """Verify admin can list users with pagination and password_hash excluded."""
    admin = _create_user(db_session, "admin_lister@example.com", role=UserRole.ADMIN)
    _create_user(db_session, "user1@example.com")
    _create_user(db_session, "user2@example.com")
    headers = _auth_header(admin)

    response = client.get("/api/admin/users?page=1&page_size=10", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["page"] == 1
    assert data["page_size"] == 10

    # Verify password_hash is not present in output
    for item in data["items"]:
        assert "password_hash" not in item
        assert "password" not in item


def test_admin_list_users_search(client, db_session):
    """Verify search filter matches email or name fields case-insensitively."""
    admin = _create_user(db_session, "admin_search@example.com", role=UserRole.ADMIN)
    _create_user(db_session, "rahul.sharma@example.com", first_name="Rahul", last_name="Sharma")
    _create_user(db_session, "priya.verma@example.com", first_name="Priya", last_name="Verma")
    headers = _auth_header(admin)

    # Search by first name
    res1 = client.get("/api/admin/users?search=rahul", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total"] == 1
    assert data1["items"][0]["email"] == "rahul.sharma@example.com"

    # Search by email domain
    res2 = client.get("/api/admin/users?search=verma", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total"] == 1
    assert data2["items"][0]["email"] == "priya.verma@example.com"


def test_admin_list_users_role_filter(client, db_session):
    """Verify filtering list by UserRole ADMIN or MEMBER."""
    admin1 = _create_user(db_session, "admin_flt1@example.com", role=UserRole.ADMIN)
    _create_user(db_session, "admin_flt2@example.com", role=UserRole.ADMIN)
    _create_user(db_session, "member_flt1@example.com", role=UserRole.MEMBER)
    headers = _auth_header(admin1)

    # Filter ADMIN
    res_admin = client.get("/api/admin/users?role=ADMIN", headers=headers)
    assert res_admin.status_code == 200
    data_a = res_admin.json()
    assert data_a["total"] == 2
    assert all(item["role"] == "admin" for item in data_a["items"])

    # Filter MEMBER
    res_member = client.get("/api/admin/users?role=MEMBER", headers=headers)
    assert res_member.status_code == 200
    data_m = res_member.json()
    assert data_m["total"] == 1
    assert data_m["items"][0]["role"] == "member"


def test_admin_list_users_invalid_role(client, db_session):
    """Verify invalid role filter query parameter returns 422."""
    admin = _create_user(db_session, "admin_inv_role@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    response = client.get("/api/admin/users?role=INVALID_ROLE", headers=headers)
    assert response.status_code == 422


def test_admin_get_user_details_success(client, db_session):
    """Verify admin can retrieve user details by ID."""
    admin = _create_user(db_session, "admin_detail@example.com", role=UserRole.ADMIN)
    target = _create_user(db_session, "target_user@example.com", first_name="Target", last_name="User")
    headers = _auth_header(admin)

    response = client.get(f"/api/admin/users/{target.id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == target.id
    assert data["email"] == "target_user@example.com"
    assert data["first_name"] == "Target"
    assert "password_hash" not in data


def test_admin_get_user_details_not_found(client, db_session):
    """Verify 404 response when querying non-existent user ID."""
    admin = _create_user(db_session, "admin_nf@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    response = client.get("/api/admin/users/999999", headers=headers)

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "user_not_found"


def test_member_authorization_rejection(client, db_session):
    """Verify MEMBER accounts are rejected with 403 on all admin user-management endpoints."""
    member = _create_user(db_session, "member_forbidden@example.com", role=UserRole.MEMBER)
    target = _create_user(db_session, "target_forb@example.com", role=UserRole.MEMBER)
    headers = _auth_header(member)

    endpoints = [
        ("GET", "/api/admin/users"),
        ("GET", f"/api/admin/users/{target.id}"),
        ("PATCH", f"/api/admin/users/{target.id}/role"),
        ("DELETE", f"/api/admin/users/{target.id}"),
    ]

    for method, path in endpoints:
        if method == "GET":
            res = client.get(path, headers=headers)
        elif method == "PATCH":
            res = client.patch(path, json={"role": "ADMIN"}, headers=headers)
        elif method == "DELETE":
            res = client.delete(path, headers=headers)
        assert res.status_code == 403
        assert res.json()["code"] == "permission_denied"


def test_unauthenticated_access_rejection(client, db_session):
    """Verify unauthenticated requests are rejected with 401."""
    target = _create_user(db_session, "target_unauth@example.com")

    endpoints = [
        ("GET", "/api/admin/users"),
        ("GET", f"/api/admin/users/{target.id}"),
        ("PATCH", f"/api/admin/users/{target.id}/role"),
        ("DELETE", f"/api/admin/users/{target.id}"),
    ]

    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        elif method == "PATCH":
            res = client.patch(path, json={"role": "ADMIN"})
        elif method == "DELETE":
            res = client.delete(path)
        assert res.status_code == 401
        assert res.json()["code"] == "missing_token"


def test_admin_change_user_role_success(client, db_session):
    """Verify admin can change another user's role from MEMBER to ADMIN."""
    admin = _create_user(db_session, "admin_role_chg@example.com", role=UserRole.ADMIN)
    target = _create_user(db_session, "promote_me@example.com", role=UserRole.MEMBER)
    headers = _auth_header(admin)

    response = client.patch(
        f"/api/admin/users/{target.id}/role",
        json={"role": "ADMIN"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == target.id
    assert data["role"] == "admin"

    # Verify database update
    db_session.refresh(target)
    assert target.role == UserRole.ADMIN


def test_admin_self_role_demotion_rejected(client, db_session):
    """Verify an admin cannot demote their own account to MEMBER."""
    admin = _create_user(db_session, "admin_self_demote@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    response = client.patch(
        f"/api/admin/users/{admin.id}/role",
        json={"role": "MEMBER"},
        headers=headers,
    )

    assert response.status_code == 409
    data = response.json()
    assert data["code"] == "self_demotion_forbidden"

    # Verify role remains ADMIN
    db_session.refresh(admin)
    assert admin.role == UserRole.ADMIN


def test_delete_safe_user_success(client, db_session):
    """Verify deleting a user without borrowing history succeeds."""
    admin = _create_user(db_session, "admin_del_safe@example.com", role=UserRole.ADMIN)
    target = _create_user(db_session, "safe_delete@example.com", role=UserRole.MEMBER)
    headers = _auth_header(admin)

    response = client.delete(f"/api/admin/users/{target.id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "User deleted successfully"

    # Verify user is removed from database
    assert db_session.get(User, target.id) is None


def test_delete_admin_self_deletion_rejected(client, db_session):
    """Verify an admin cannot delete their own account."""
    admin = _create_user(db_session, "admin_self_del@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    response = client.delete(f"/api/admin/users/{admin.id}", headers=headers)

    assert response.status_code == 409
    data = response.json()
    assert data["code"] == "self_deletion_forbidden"

    # Verify admin still exists
    assert db_session.get(User, admin.id) is not None


def test_delete_user_with_borrowing_history_rejected(client, db_session):
    """Verify user with borrowing history cannot be deleted (preserves history)."""
    admin = _create_user(db_session, "admin_del_hist@example.com", role=UserRole.ADMIN)
    borrower = _create_user(db_session, "borrower_del@example.com", role=UserRole.MEMBER)
    book = Book(title="History Preserved Book", author="Author", isbn="9787777777777", total_quantity=5, available_quantity=4)
    db_session.add(book)
    db_session.commit()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record = BorrowingRecord(
        user_id=borrower.id,
        book_id=book.id,
        issue_date=now - timedelta(days=5),
        due_date=now + timedelta(days=9),
        status=BorrowingStatus.BORROWED,
    )
    db_session.add(record)
    db_session.commit()

    headers = _auth_header(admin)
    response = client.delete(f"/api/admin/users/{borrower.id}", headers=headers)

    assert response.status_code == 409
    data = response.json()
    assert data["code"] == "user_has_borrowing_history"

    # Verify borrower and record still exist
    assert db_session.get(User, borrower.id) is not None
    assert db_session.get(BorrowingRecord, record.id) is not None
