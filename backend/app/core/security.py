"""
Security utilities: password hashing and JWT token handling.
All cryptographic concerns live here so services stay clean.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.exceptions import InvalidTokenError, TokenExpiredError

settings = get_settings()

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    pwd_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plain-text password matches the hash."""
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password=password_byte_enc, hashed_password=hashed_password_byte_enc)


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token for the given subject (user ID / email)."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> str:
    """
    Decode and verify a JWT access token.

    Returns:
        The 'sub' claim (user identifier).

    Raises:
        TokenExpiredError: if the token has passed its expiry time.
        InvalidTokenError: if the token is malformed or signature is invalid.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        subject: str | None = payload.get("sub")
        if subject is None:
            raise InvalidTokenError()
        return subject
    except JWTError as exc:
        # jose raises ExpiredSignatureError (a subclass of JWTError) for expired tokens
        if "expired" in str(exc).lower():
            raise TokenExpiredError() from exc
        raise InvalidTokenError() from exc
