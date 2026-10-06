"""Comprehensive test suite for the Admin Inventory / Book Management API."""

from datetime import datetime, timezone, timedelta

import pytest

from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User, UserRole
from app.utils.jwt_utils import create_access_token


def _create_user(db, email="inventory_admin@example.com", role=UserRole.ADMIN):
    """Helper to create and persist a user."""
    user = User(
        email=email,
        password_hash="hashed_pw_secret_123",
        first_name="Admin",
        last_name="User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_book(
    db,
    title="Clean Code",
    author="Robert C. Martin",
    isbn="9780132350884",
    genre="Software",
    total_quantity=5,
    available_quantity=5,
):
    """Helper to create and persist a book."""
    book = Book(
        title=title,
        author=author,
        isbn=isbn,
        genre=genre,
        description="A Handbook of Agile Software Craftsmanship",
        total_quantity=total_quantity,
        available_quantity=available_quantity,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def _auth_header(user: User) -> dict:
    """Helper to construct JWT authorization header."""
    token = create_access_token(user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------

def test_inventory_authorization_access(client, db_session):
    """Verify admin can access inventory, member receives 403, unauthenticated receives 401."""
    admin = _create_user(db_session, "inv_admin@example.com", role=UserRole.ADMIN)
    member = _create_user(db_session, "inv_member@example.com", role=UserRole.MEMBER)
    book = _create_book(db_session, isbn="9780000000001")

    admin_headers = _auth_header(admin)
    member_headers = _auth_header(member)

    # 1. Admin access succeeds
    res_admin = client.get("/api/admin/books", headers=admin_headers)
    assert res_admin.status_code == 200

    # 2. Member access rejected (403)
    endpoints = [
        ("GET", "/api/admin/books"),
        ("GET", f"/api/admin/books/{book.id}"),
        ("POST", "/api/admin/books"),
        ("PATCH", f"/api/admin/books/{book.id}"),
        ("DELETE", f"/api/admin/books/{book.id}"),
    ]
    for method, path in endpoints:
        if method == "GET":
            r = client.get(path, headers=member_headers)
        elif method == "POST":
            r = client.post(path, json={"title": "T", "author": "A", "isbn": "9781111111111"}, headers=member_headers)
        elif method == "PATCH":
            r = client.patch(path, json={"title": "Updated"}, headers=member_headers)
        elif method == "DELETE":
            r = client.delete(path, headers=member_headers)
        assert r.status_code == 403

    # 3. Unauthenticated access rejected (401)
    for method, path in endpoints:
        if method == "GET":
            r = client.get(path)
        elif method == "POST":
            r = client.post(path, json={"title": "T", "author": "A", "isbn": "9781111111111"})
        elif method == "PATCH":
            r = client.patch(path, json={"title": "Updated"})
        elif method == "DELETE":
            r = client.delete(path)
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# List & Filter Tests
# ---------------------------------------------------------------------------

def test_list_books_pagination_search_and_filtering(client, db_session):
    """Verify list books endpoint supports pagination, search, genre filter, and availability filter."""
    admin = _create_user(db_session, "inv_lister@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    _create_book(db_session, title="Python Crash Course", author="Eric Matthes", isbn="9781593279288", genre="Programming", total_quantity=3, available_quantity=3)
    _create_book(db_session, title="Dune", author="Frank Herbert", isbn="9780441172719", genre="Sci-Fi", total_quantity=2, available_quantity=0)
    _create_book(db_session, title="Fluent Python", author="Luciano Ramalho", isbn="9781491946008", genre="Programming", total_quantity=5, available_quantity=2)

    # List all
    res = client.get("/api/admin/books?page=1&page_size=10", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # Search by author
    res_s = client.get("/api/admin/books?search=Matthes", headers=headers)
    assert res_s.status_code == 200
    assert res_s.json()["total"] == 1
    assert res_s.json()["items"][0]["title"] == "Python Crash Course"

    # Filter by genre
    res_g = client.get("/api/admin/books?genre=Programming", headers=headers)
    assert res_g.status_code == 200
    assert res_g.json()["total"] == 2

    # Filter by availability
    res_avail_true = client.get("/api/admin/books?available=true", headers=headers)
    assert res_avail_true.status_code == 200
    assert res_avail_true.json()["total"] == 2

    res_avail_false = client.get("/api/admin/books?available=false", headers=headers)
    assert res_avail_false.status_code == 200
    assert res_avail_false.json()["total"] == 1
    assert res_avail_false.json()["items"][0]["title"] == "Dune"


# ---------------------------------------------------------------------------
# Get Book Details Tests
# ---------------------------------------------------------------------------

def test_get_book_details_success_and_not_found(client, db_session):
    """Verify retrieving existing book returns details and non-existent returns 404."""
    admin = _create_user(db_session, "inv_getter@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)
    book = _create_book(db_session, title="Refactoring", isbn="9780201485677")

    res_ok = client.get(f"/api/admin/books/{book.id}", headers=headers)
    assert res_ok.status_code == 200
    assert res_ok.json()["title"] == "Refactoring"
    assert res_ok.json()["is_available"] is True

    res_nf = client.get("/api/admin/books/99999", headers=headers)
    assert res_nf.status_code == 404
    assert res_nf.json()["code"] == "book_not_found"


# ---------------------------------------------------------------------------
# Add Book Tests
# ---------------------------------------------------------------------------

def test_create_book_success_and_validations(client, db_session):
    """Verify creating a new book, available_quantity default, invalid quantity rejection, and duplicate ISBN rejection."""
    admin = _create_user(db_session, "inv_creator@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    # Successful creation (available_quantity defaults to total_quantity)
    payload = {
        "title": "Design Patterns",
        "author": "Erich Gamma",
        "isbn": "9780201633610",
        "genre": "Software",
        "total_quantity": 4,
    }
    res = client.post("/api/admin/books", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["total_quantity"] == 4
    assert data["available_quantity"] == 4

    # Duplicate ISBN rejection
    res_dup = client.post("/api/admin/books", json=payload, headers=headers)
    assert res_dup.status_code == 409
    assert res_dup.json()["code"] == "duplicate_isbn"

    # Invalid available_quantity > total_quantity rejection
    invalid_payload = {
        "title": "Bad Quantity Book",
        "author": "Unknown",
        "isbn": "9780000000009",
        "total_quantity": 3,
        "available_quantity": 10,
    }
    res_inv = client.post("/api/admin/books", json=invalid_payload, headers=headers)
    assert res_inv.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Update Book Metadata Tests
# ---------------------------------------------------------------------------

def test_update_book_metadata(client, db_session):
    """Verify updating title, author, genre, description, and ISBN."""
    admin = _create_user(db_session, "inv_updater@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)
    book = _create_book(db_session, title="Old Title", author="Old Author", isbn="9781111222333")

    update_payload = {
        "title": "New Title",
        "author": "New Author",
        "genre": "Architecture",
    }
    res = client.patch(f"/api/admin/books/{book.id}", json=update_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "New Title"
    assert data["author"] == "New Author"
    assert data["genre"] == "Architecture"


# ---------------------------------------------------------------------------
# Inventory Quantity Update Tests (Increase & Decrease)
# ---------------------------------------------------------------------------

def test_update_book_quantity_increase_preserves_borrowings(client, db_session):
    """Verify increasing total_quantity preserves active borrowings: old total=5, old available=2 (borrowed=3) -> new total=8 results in new available=5."""
    admin = _create_user(db_session, "inv_qty_inc@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    # Book with 5 total, 2 available => 3 currently borrowed
    book = _create_book(db_session, title="Borrowed Book", isbn="9785555555555", total_quantity=5, available_quantity=2)

    # Increase total_quantity to 8
    res = client.patch(f"/api/admin/books/{book.id}", json={"total_quantity": 8}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_quantity"] == 8
    assert data["available_quantity"] == 5  # 8 - 3 = 5


def test_update_book_quantity_decrease(client, db_session):
    """Verify valid decrease works, but decreasing total_quantity below active borrowings is rejected."""
    admin = _create_user(db_session, "inv_qty_dec@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)

    # Book with 5 total, 2 available => 3 currently borrowed
    book = _create_book(db_session, title="Borrowed Book 2", isbn="9786666666666", total_quantity=5, available_quantity=2)

    # Valid decrease to 4 => new available should be 4 - 3 = 1
    res_valid = client.patch(f"/api/admin/books/{book.id}", json={"total_quantity": 4}, headers=headers)
    assert res_valid.status_code == 200
    data = res_valid.json()
    assert data["total_quantity"] == 4
    assert data["available_quantity"] == 1

    # Invalid decrease to 2 (borrowed is 3) => REJECTED
    res_invalid = client.patch(f"/api/admin/books/{book.id}", json={"total_quantity": 2}, headers=headers)
    assert res_invalid.status_code in (400, 409)


def test_inventory_quantity_invariant_enforced(client, db_session):
    """Verify API prevents available_quantity < 0 or available_quantity > total_quantity."""
    admin = _create_user(db_session, "inv_invariant@example.com", role=UserRole.ADMIN)
    headers = _auth_header(admin)
    book = _create_book(db_session, isbn="9787777888999", total_quantity=5, available_quantity=5)

    # Attempt available_quantity > total_quantity
    res_over = client.patch(f"/api/admin/books/{book.id}", json={"available_quantity": 10}, headers=headers)
    assert res_over.status_code in (400, 422)

    # Attempt available_quantity < 0
    res_neg = client.patch(f"/api/admin/books/{book.id}", json={"available_quantity": -1}, headers=headers)
    assert res_neg.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Delete Book Safety Tests
# ---------------------------------------------------------------------------

def test_delete_book_safety(client, db_session):
    """Verify non-existent returns 404, active borrowed book cannot be deleted, historical record book cannot be deleted, unborrowed book deletes cleanly."""
    admin = _create_user(db_session, "inv_deleter@example.com", role=UserRole.ADMIN)
    borrower = User(email="borrower_inv@example.com", password_hash="secret", first_name="B", last_name="U", role=UserRole.MEMBER, is_active=True)
    db_session.add(borrower)
    db_session.commit()

    headers = _auth_header(admin)

    # 1. Non-existent book -> 404
    res_nf = client.delete("/api/admin/books/99999", headers=headers)
    assert res_nf.status_code == 404

    # 2. Book with active BORROWED record -> 409
    book_active = _create_book(db_session, title="Active Borrow Book", isbn="9780000000111")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rec_active = BorrowingRecord(
        user_id=borrower.id,
        book_id=book_active.id,
        issue_date=now - timedelta(days=1),
        due_date=now + timedelta(days=13),
        status=BorrowingStatus.BORROWED,
    )
    db_session.add(rec_active)
    db_session.commit()

    res_act = client.delete(f"/api/admin/books/{book_active.id}", headers=headers)
    assert res_act.status_code == 409
    assert res_act.json()["code"] == "book_has_active_borrowings"

    # 3. Book with historical RETURNED record -> 409 (preserves history)
    book_hist = _create_book(db_session, title="Historical Book", isbn="9780000000222")
    rec_hist = BorrowingRecord(
        user_id=borrower.id,
        book_id=book_hist.id,
        issue_date=now - timedelta(days=20),
        due_date=now - timedelta(days=6),
        return_date=now - timedelta(days=5),
        status=BorrowingStatus.RETURNED,
    )
    db_session.add(rec_hist)
    db_session.commit()

    res_hist = client.delete(f"/api/admin/books/{book_hist.id}", headers=headers)
    assert res_hist.status_code == 409
    assert res_hist.json()["code"] == "book_has_borrowing_history"

    # 4. Safe book deletion (no borrowing records) -> 200
    book_safe = _create_book(db_session, title="Safe To Delete", isbn="9780000000333")
    res_safe = client.delete(f"/api/admin/books/{book_safe.id}", headers=headers)
    assert res_safe.status_code == 200
    assert db_session.get(Book, book_safe.id) is None
