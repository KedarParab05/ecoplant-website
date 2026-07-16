"""
middleware/validators.py — Shared input validation helpers
"""

import re
from fastapi import HTTPException

# ── Regex patterns ─────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
# Password: min 8 chars, at least 1 letter + 1 digit
STRONG_PW_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def validate_email(email: str) -> str:
    """Validate and normalise an email address."""
    if not email or not isinstance(email, str):
        raise HTTPException(400, "Valid email is required")
    email = email.lower().strip()
    if len(email) > 254:
        raise HTTPException(400, "Email is too long")
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Invalid email format")
    return email


def validate_password(password: str, field: str = "Password") -> str:
    """Enforce minimum password security requirements."""
    if not password or not isinstance(password, str):
        raise HTTPException(400, f"{field} is required")
    if len(password) < 8:
        raise HTTPException(400, f"{field} must be at least 8 characters")
    if len(password) > 128:
        raise HTTPException(400, f"{field} is too long")
    if not STRONG_PW_RE.match(password):
        raise HTTPException(400, f"{field} must contain at least one letter and one number")
    return password


def validate_name(name: str) -> str:
    """Validate a user display name."""
    if not name or not isinstance(name, str):
        raise HTTPException(400, "Name is required")
    name = name.strip()
    if len(name) < 2:
        raise HTTPException(400, "Name must be at least 2 characters")
    if len(name) > 100:
        raise HTTPException(400, "Name is too long")
    # Block HTML/script injection in name
    if re.search(r"[<>\"'`]|javascript:|on\w+=", name, re.IGNORECASE):
        raise HTTPException(400, "Name contains invalid characters")
    return name


def validate_text(text: str, field: str = "Text", min_len: int = 5, max_len: int = 1000) -> str:
    """Validate a generic text field."""
    if not text or not isinstance(text, str):
        raise HTTPException(400, f"{field} is required")
    text = text.strip()
    if len(text) < min_len:
        raise HTTPException(400, f"{field} must be at least {min_len} characters")
    if len(text) > max_len:
        raise HTTPException(400, f"{field} must be at most {max_len} characters")
    return text


def validate_object_id(oid: str, field: str = "ID") -> str:
    """Validate a MongoDB ObjectId string."""
    if not oid or not re.match(r"^[a-f0-9]{24}$", oid, re.IGNORECASE):
        # Also accept UUIDs (json fallback)
        if not re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            oid, re.IGNORECASE
        ):
            raise HTTPException(400, f"Invalid {field} format")
    return oid
