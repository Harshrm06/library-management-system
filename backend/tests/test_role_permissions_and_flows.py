"""Tests verifying admin & member permissions, borrowing, book CRUD, and member creation."""

import itertools
from datetime import datetime, timezone
import pytest

from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User, UserRole
from app.utils.jwt_utils import create_access_token

_isbn_counter = itertools.count(50000)


def _create_user(db, email="user@example.com", role=UserRole.MEMBER):
    user = User(
        email=email,
        password_hash="hashed_pw_secret_123",
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_book(db, title="Test Book", total=5, available=5):
    book = Book(
        title=title,
        author="Test Author",
        isbn=f"978{int(datetime.now(timezone.utc).timestamp())}{next(_isbn_counter)}",
        genre="Fiction",
        total_quantity=total,
        available_quantity=available,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def _auth_header(user: User) -> dict:
    token = create_access_token(user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_create_book(client, db_session):
    admin = _create_user(db_session, "admin_book_cr@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)
    isbn = f"978{next(_isbn_counter):010d}"
    payload = {
        "title": "New Book by Admin",
        "author": "Great Author",
        "isbn": isbn,
        "genre": "Science",
        "total_quantity": 4,
        "available_quantity": 4,
        "published_year": 2024,
    }
    response = client.post("/api/admin/books", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Book by Admin"
    assert data["total_quantity"] == 4
    assert data["available_quantity"] == 4


def test_admin_can_update_and_delete_book(client, db_session):
    admin = _create_user(db_session, "admin_book_up@example.com", role=UserRole.ADMIN)
    book = _create_book(db_session, "Updatable Book", total=3, available=3)
    headers = _auth_header(admin)

    # Update
    update_res = client.patch(
        f"/api/admin/books/{book.id}",
        json={"title": "Updated Title", "total_quantity": 5, "available_quantity": 5},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Title"
    assert update_res.json()["total_quantity"] == 5

    # Delete
    del_res = client.delete(f"/api/admin/books/{book.id}", headers=headers)
    assert del_res.status_code == 200
    assert db_session.get(Book, book.id) is None


def test_non_admin_cannot_manage_books(client, db_session):
    member = _create_user(db_session, "member_book_block@example.com", role=UserRole.MEMBER)
    book = _create_book(db_session, "Protected Book", total=2, available=2)
    headers = _auth_header(member)

    # Member cannot create
    res_cr = client.post(
        "/api/admin/books",
        json={"title": "Hack", "author": "Hacker", "isbn": "9781234567890", "total_quantity": 1},
        headers=headers,
    )
    assert res_cr.status_code == 403

    # Member cannot update
    res_up = client.patch(f"/api/admin/books/{book.id}", json={"title": "Hacked"}, headers=headers)
    assert res_up.status_code == 403

    # Member cannot delete
    res_del = client.delete(f"/api/admin/books/{book.id}", headers=headers)
    assert res_del.status_code == 403


def test_admin_can_borrow_and_return_books(client, db_session):
    admin = _create_user(db_session, "admin_borrower@example.com", role=UserRole.ADMIN)
    book = _create_book(db_session, "Admin Loan Book", total=3, available=3)
    headers = _auth_header(admin)

    # Admin borrows book
    borrow_res = client.post(f"/api/borrow/{book.id}", headers=headers)
    assert borrow_res.status_code == 201
    b_data = borrow_res.json()
    assert b_data["book_id"] == book.id
    assert b_data["status"] == "BORROWED"
    assert b_data["remaining_available_quantity"] == 2

    # Verify inventory decreased
    db_session.refresh(book)
    assert book.available_quantity == 2

    # Verify borrowing record belongs to admin
    record_id = b_data["id"]
    record = db_session.get(BorrowingRecord, record_id)
    assert record.user_id == admin.id

    # Admin returns book
    return_res = client.post(f"/api/return/{record_id}", headers=headers)
    assert return_res.status_code == 200
    r_data = return_res.json()
    assert r_data["status"] == "RETURNED"

    # Verify inventory increased
    db_session.refresh(book)
    assert book.available_quantity == 3


def test_members_can_borrow_and_return_books(client, db_session):
    member = _create_user(db_session, "member_borrower@example.com", role=UserRole.MEMBER)
    book = _create_book(db_session, "Member Loan Book", total=2, available=2)
    headers = _auth_header(member)

    # Member borrows
    borrow_res = client.post(f"/api/borrow/{book.id}", headers=headers)
    assert borrow_res.status_code == 201
    rec_id = borrow_res.json()["id"]

    db_session.refresh(book)
    assert book.available_quantity == 1

    # Member returns
    return_res = client.post(f"/api/return/{rec_id}", headers=headers)
    assert return_res.status_code == 200

    db_session.refresh(book)
    assert book.available_quantity == 2


def test_user_cannot_return_another_users_loan(client, db_session):
    user1 = _create_user(db_session, "user1_loan@example.com", role=UserRole.MEMBER)
    user2 = _create_user(db_session, "user2_thief@example.com", role=UserRole.MEMBER)
    book = _create_book(db_session, "Exclusive Book", total=2, available=2)

    # user1 borrows
    borrow_res = client.post(f"/api/borrow/{book.id}", headers=_auth_header(user1))
    assert borrow_res.status_code == 201
    rec_id = borrow_res.json()["id"]

    # user2 tries to return
    ret_res = client.post(f"/api/return/{rec_id}", headers=_auth_header(user2))
    assert ret_res.status_code == 403
    assert ret_res.json()["code"] == "unauthorized_return"


def test_member_cannot_view_another_users_borrowing_history(client, db_session):
    user1 = _create_user(db_session, "user1_hist@example.com", role=UserRole.MEMBER)
    user2 = _create_user(db_session, "user2_hist@example.com", role=UserRole.MEMBER)
    book = _create_book(db_session, "Hist Book", total=2, available=2)

    # user1 borrows
    client.post(f"/api/borrow/{book.id}", headers=_auth_header(user1))

    # user2 checks their own history: must be empty
    res2 = client.get("/api/borrow/history", headers=_auth_header(user2))
    assert res2.status_code == 200
    assert len(res2.json()["items"]) == 0

    # user1 checks their own history: contains 1 item
    res1 = client.get("/api/borrow/history", headers=_auth_header(user1))
    assert res1.status_code == 200
    assert len(res1.json()["items"]) == 1


def test_admin_can_create_member_account(client, db_session):
    admin = _create_user(db_session, "admin_user_creator@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    new_member_payload = {
        "email": "brand_new_member@example.com",
        "password": "Password123",
        "first_name": "New",
        "last_name": "Member",
        "phone": "+1234567890",
        "address": "42 Library St",
    }
    response = client.post("/api/admin/users", json=new_member_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "brand_new_member@example.com"
    assert data["first_name"] == "New"
    assert data["role"] == "member"
    assert "password" not in data
    assert "password_hash" not in data

    # Verify user in database
    created_user = db_session.get(User, data["id"])
    assert created_user is not None
    assert created_user.role == UserRole.MEMBER


def test_member_cannot_create_member_account(client, db_session):
    member = _create_user(db_session, "member_attempt_create@example.com", role=UserRole.MEMBER)
    headers = _auth_header(member)

    payload = {
        "email": "illegal_member@example.com",
        "password": "Password123",
        "first_name": "Illegal",
        "last_name": "Member",
    }
    # Direct call to admin users endpoint
    res_admin_ep = client.post("/api/admin/users", json=payload, headers=headers)
    assert res_admin_ep.status_code == 403

    # Call to /auth/register
    res_reg_ep = client.post("/api/auth/register", json=payload, headers=headers)
    assert res_reg_ep.status_code == 403


def test_cannot_assign_admin_role_on_registration(client, db_session):
    admin = _create_user(db_session, "admin_creator_check@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    payload = {
        "email": "try_admin@example.com",
        "password": "Password123",
        "first_name": "Wannabe",
        "last_name": "Admin",
        "role": "admin",
    }
    # role is forbidden in UserRegisterRequest extra fields
    res = client.post("/api/admin/users", json=payload, headers=headers)
    assert res.status_code == 422


def test_duplicate_active_borrowing_rejected(client, db_session):
    member = _create_user(db_session, "dup_borrower@example.com", role=UserRole.MEMBER)
    book = _create_book(db_session, "Single Copy Book", total=3, available=3)
    headers = _auth_header(member)

    # First borrow succeeds
    res1 = client.post(f"/api/borrow/{book.id}", headers=headers)
    assert res1.status_code == 201

    # Second borrow of same book while first is active fails with 409
    res2 = client.post(f"/api/borrow/{book.id}", headers=headers)
    assert res2.status_code == 409
    assert res2.json()["code"] == "already_borrowed"


def test_out_of_stock_borrowing_rejected(client, db_session):
    m1 = _create_user(db_session, "m1_stock@example.com", role=UserRole.MEMBER)
    m2 = _create_user(db_session, "m2_stock@example.com", role=UserRole.MEMBER)
    book = _create_book(db_session, "Scarce Book", total=1, available=1)

    # m1 borrows last copy
    res1 = client.post(f"/api/borrow/{book.id}", headers=_auth_header(m1))
    assert res1.status_code == 201

    # m2 attempts to borrow out-of-stock book
    res2 = client.post(f"/api/borrow/{book.id}", headers=_auth_header(m2))
    assert res2.status_code == 400
    assert res2.json()["code"] == "book_unavailable"


def test_inventory_invariants_preserved(client, db_session):
    admin = _create_user(db_session, "admin_invariant@example.com", role=UserRole.ADMIN)
    m1 = _create_user(db_session, "m1_invariant@example.com", role=UserRole.MEMBER)
    m2 = _create_user(db_session, "m2_invariant@example.com", role=UserRole.MEMBER)
    book = _create_book(db_session, "Invariant Book", total=4, available=4)

    # 2 members borrow 1 copy each: borrowed = 2, available = 2
    res_b1 = client.post(f"/api/borrow/{book.id}", headers=_auth_header(m1))
    assert res_b1.status_code == 201
    res_b2 = client.post(f"/api/borrow/{book.id}", headers=_auth_header(m2))
    assert res_b2.status_code == 201

    headers = _auth_header(admin)

    # Admin cannot set total_quantity (1) < borrowed copies (2)
    res_reduce = client.patch(
        f"/api/admin/books/{book.id}",
        json={"total_quantity": 1},
        headers=headers,
    )
    assert res_reduce.status_code == 409
    assert res_reduce.json()["code"] == "quantity_below_borrowed"

    # Admin cannot set available_quantity > total_quantity
    res_overflow = client.patch(
        f"/api/admin/books/{book.id}",
        json={"available_quantity": 10},
        headers=headers,
    )
    assert res_overflow.status_code in (400, 422)

    # Admin cannot delete book with active borrowing
    res_del = client.delete(f"/api/admin/books/{book.id}", headers=headers)
    assert res_del.status_code == 409
    assert res_del.json()["code"] in ("book_has_active_borrowings", "book_has_borrowing_history")
