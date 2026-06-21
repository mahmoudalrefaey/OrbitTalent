"""Usage router — token/cost tracking dashboard data."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser
from app.schemas import UsageOut
from app.services import usage as usage_svc

router = APIRouter(tags=["usage"])


@router.get("/usage", response_model=UsageOut)
def get_usage(user: CurrentUser, db: Session = Depends(get_db)) -> UsageOut:
    """Aggregate LLM token usage + estimated cost for the cost dashboard."""
    return usage_svc.build_usage_out(db, tenant_id=user.tenant_id)
