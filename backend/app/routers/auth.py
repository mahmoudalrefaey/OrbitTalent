"""Auth router — register / login / logout / me.

Sessions are JWTs in an httpOnly, SameSite=Lax cookie. Registration creates a
dedicated Tenant per user (the data-isolation boundary). Public endpoints:
register + login. `me` requires the session cookie.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import CurrentUser
from app.models import Tenant, User
from app.schemas import LoginRequest, RegisterRequest, UserOut
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=auth.COOKIE_NAME,
        value=auth.create_access_token(user_id),
        max_age=auth.cookie_max_age(),
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> UserOut:
    email = payload.email.lower().strip()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # Each user gets their own tenant → isolated jobs/candidates/usage.
    tenant = Tenant(name=payload.name or email)
    db.add(tenant)
    db.flush()  # assign tenant.id without a second round-trip

    user = User(
        tenant_id=tenant.id,
        email=email,
        hashed_password=auth.hash_password(payload.password),
        name=payload.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _set_session_cookie(response, user.id)
    return UserOut.model_validate(user)


@router.post("/login", response_model=UserOut)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> UserOut:
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    # Generic failure message — do not reveal whether the email exists.
    if user is None or not auth.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    _set_session_cookie(response, user.id)
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> FastAPIResponse:
    resp = FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)
    resp.delete_cookie(auth.COOKIE_NAME, path="/")
    return resp


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
