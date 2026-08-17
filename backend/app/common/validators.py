"""
Shared validators for reuse across domain schemas.
"""
import re

# South African mobile number pattern: starts with 06/07/08, 10 digits
_SA_MOBILE_RE = re.compile(r"^0[678]\d{8}$")


def validate_sa_mobile(phone: str) -> str:
    """Validate a South African mobile number format (e.g. 0821234567)."""
    cleaned = re.sub(r"[\s\-()]", "", phone)
    if not _SA_MOBILE_RE.match(cleaned):
        raise ValueError(
            f"'{phone}' is not a valid South African mobile number. "
            "Expected format: 0821234567"
        )
    return cleaned


def validate_password_strength(password: str) -> str:
    """
    Enforce minimum password requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one digit
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
    return password
