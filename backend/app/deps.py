"""Shared FastAPI dependencies — primarily authentication."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services import auth

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Cookie"},
)


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    """Resolve the logged-in user from the session cookie, or 401."""
    token = request.cookies.get(auth.COOKIE_NAME)
    if not token:
        raise _UNAUTH
    user_id = auth.decode_token(token)
    if user_id is None:
        raise _UNAUTH
    user = db.get(User, user_id)
    if user is None:
        raise _UNAUTH
    return user


# Convenience alias for route signatures: `user: CurrentUser`.
CurrentUser = Annotated[User, Depends(get_current_user)]
