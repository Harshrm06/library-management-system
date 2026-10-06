"""Reusable validation helpers for request payloads.

These are plain functions so they can be used from Pydantic validators,
controllers, or one-off scripts::

    >>> validate_email_format("member@example.com")
    True
    >>> validate_password_strength("secretpass")
    (False, 'Password must contain at least one number')
"""

from __future__ import annotations

import re

EMAIL_REGEX: re.Pattern[str] = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
ISBN_DIGITS_REGEX: re.Pattern[str] = re.compile(r"^(?:\d{9}[\dXx]|\d{13})$")
VALID_ROLES: frozenset[str] = frozenset({"admin", "member"})
MIN_PASSWORD_LENGTH: int = 6


def validate_email_format(email: str) -> bool:
    """Check that an email address looks well formed.

    Args:
        email: The address to validate.

    Returns:
        bool: ``True`` when the address matches ``local@domain.tld``.

    Example:
        >>> validate_email_format("member@example.com")
        True
        >>> validate_email_format("member@example")
        False
    """
    if not isinstance(email, str):
        return False
    candidate: str = email.strip()
    if not candidate or len(candidate) > 255:
        return False
    return EMAIL_REGEX.match(candidate) is not None


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Check a password against the minimum strength policy.

    Policy: at least 6 characters, at least one letter and at least one digit.

    Args:
        password: The plaintext password to check.

    Returns:
        tuple[bool, str]: ``(is_valid, message)``. The message is empty when
        the password is valid and otherwise explains the first failure.

    Example:
        >>> validate_password_strength("Test1234")
        (True, '')
        >>> validate_password_strength("secretpass")
        (False, 'Password must contain at least one number')
        >>> validate_password_strength("1234567")
        (False, 'Password must contain at least one letter')
        >>> validate_password_strength("short")
        (False, 'Password must be at least 6 characters long')
    """
    if not isinstance(password, str) or not password:
        return False, "Password is required"
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
    if not any(character.isalpha() for character in password):
        return False, "Password must contain at least one letter"
    if not any(character.isdigit() for character in password):
        return False, "Password must contain at least one number"
    return True, ""


def validate_role(role: str) -> bool:
    """Check that a role is one the application supports.

    Args:
        role: The role to validate, case-insensitive.

    Returns:
        bool: ``True`` for ``admin`` or ``member``.

    Example:
        >>> validate_role("admin")
        True
        >>> validate_role("librarian")
        False
    """
    if not isinstance(role, str):
        return False
    return role.strip().lower() in VALID_ROLES


def validate_isbn_format(isbn: str) -> bool:
    """Check that an ISBN is 10 or 13 digits, hyphens and spaces allowed.

    Only the shape is checked - the check digit is deliberately not verified,
    because libraries routinely hold imperfectly scanned ISBNs and rejecting
    them would block a real catalogue entry.

    Args:
        isbn: The identifier to validate.

    Returns:
        bool: ``True`` for a 10 digit ISBN (trailing ``X`` allowed) or a 13
        digit one.

    Example:
        >>> validate_isbn_format("978-0-441-01359-3")
        True
        >>> validate_isbn_format("12345")
        False
    """
    if not isinstance(isbn, str):
        return False
    candidate: str = isbn.strip().replace("-", "").replace(" ", "")
    return ISBN_DIGITS_REGEX.match(candidate) is not None


def normalize_isbn(isbn: str) -> str:
    """Return an ISBN in its canonical, storage-ready form.

    Hyphens and spaces are removed and the value is upper-cased so ISBN-10
    checks digits written as ``x`` compare equal to those written as ``X``.

    Args:
        isbn: The identifier to normalize.

    Returns:
        str: The bare digits, or an empty string for non-string input.

    Example:
        >>> normalize_isbn("978-0-441-01359-3")
        '9780441013593'
    """
    if not isinstance(isbn, str):
        return ""
    return isbn.strip().replace("-", "").replace(" ", "").upper()