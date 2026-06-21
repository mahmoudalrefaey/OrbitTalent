"""Auth primitives: password hashing + session JWTs.

Sessions are stateless JWTs (HS256) carried in an httpOnly cookie. The token's
`sub` is the user id. Kept deliberately small — no roles/claims beyond identity
and expiry (RBAC is out of scope for this MVP).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()

COOKIE_NAME = "ot_session"
_ALGORITHM = "HS256"


def _bcrypt_safe(plain: str) -> bytes:
    """bcrypt only uses the first 72 bytes; truncate explicitly."""
    return plain.encode("utf-8")[:72]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_bcrypt_safe(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_bcrypt_safe(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str) -> int | None:
    """Return the user id from a valid token, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (jwt.PyJWTError, ValueError):
        return None


def cookie_max_age() -> int:
    return settings.jwt_expire_days * 24 * 3600
