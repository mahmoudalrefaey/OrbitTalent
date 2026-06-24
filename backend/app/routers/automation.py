"""Automation rules CRUD (tenant-scoped)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser
from app.models import AutomationRule, Candidate, Job, ScoreStatus
from app.schemas import (
    ApplyRulesRequest,
    ApplyRulesResult,
    AutomationRuleBase,
    AutomationRuleOut,
)
from app.services import automation as automation_svc

router = APIRouter(prefix="/automation-rules", tags=["automation"])


def _owned_rule(db: Session, rule_id: int, tenant_id: int) -> AutomationRule:
    rule = db.get(AutomationRule, rule_id)
    if rule is None or rule.tenant_id != tenant_id:
        raise HTTPException(404, "Rule not found")
    return rule


@router.get("", response_model=list[AutomationRuleOut])
def list_rules(
    user: CurrentUser, db: Session = Depends(get_db), job_id: int | None = None
) -> list[AutomationRuleOut]:
    q = select(AutomationRule).where(AutomationRule.tenant_id == user.tenant_id)
    if job_id is not None:
        q = q.where(AutomationRule.job_id == job_id)
    rules = db.scalars(q.order_by(AutomationRule.priority.desc(), AutomationRule.id)).all()
    return [AutomationRuleOut.model_validate(r) for r in rules]


@router.post("", response_model=AutomationRuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: AutomationRuleBase, user: CurrentUser, db: Session = Depends(get_db)
) -> AutomationRuleOut:
    if payload.job_id is not None:
        job = db.get(Job, payload.job_id)
        if job is None or job.tenant_id != user.tenant_id:
            raise HTTPException(400, "Invalid job")
    rule = AutomationRule(
        tenant_id=user.tenant_id,
        job_id=payload.job_id,
        name=payload.name,
        trigger_json=payload.trigger_json,
        action_json=payload.action_json,
        enabled=payload.enabled,
        priority=payload.priority,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return AutomationRuleOut.model_validate(rule)


@router.post("/apply", response_model=ApplyRulesResult)
def apply_rules_now(
    payload: ApplyRulesRequest, user: CurrentUser, db: Session = Depends(get_db)
) -> ApplyRulesResult:
    """Apply automation rules to a job's already-uploaded candidates.

    Triggers evaluation only — rules are not modified or removed, so they keep
    firing automatically on future CVs. Applies to scored, non-terminal
    candidates (terminal stages are skipped inside the service).
    """
    job = db.get(Job, payload.job_id)
    if job is None or job.tenant_id != user.tenant_id:
        raise HTTPException(404, "Job not found")

    # If specific rules were named, verify each belongs to the caller's tenant.
    if payload.rule_ids:
        owned = db.scalars(
            select(AutomationRule.id).where(
                AutomationRule.id.in_(payload.rule_ids),
                AutomationRule.tenant_id == user.tenant_id,
            )
        ).all()
        missing = set(payload.rule_ids) - set(owned)
        if missing:
            raise HTTPException(404, "Rule not found")

    candidates = list(
        db.scalars(
            select(Candidate).where(
                Candidate.tenant_id == user.tenant_id,
                Candidate.job_id == payload.job_id,
                Candidate.score_status == ScoreStatus.scored,
            )
        ).all()
    )

    result = automation_svc.apply_rules_to_candidates(
        db,
        candidates,
        tenant_id=user.tenant_id,
        job_id=payload.job_id,
        rule_ids=payload.rule_ids,
    )
    db.commit()
    return ApplyRulesResult(**result)


@router.put("/{rule_id}", response_model=AutomationRuleOut)
def update_rule(
    rule_id: int,
    payload: AutomationRuleBase,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> AutomationRuleOut:
    rule = _owned_rule(db, rule_id, user.tenant_id)
    rule.name = payload.name
    rule.job_id = payload.job_id
    rule.trigger_json = payload.trigger_json
    rule.action_json = payload.action_json
    rule.enabled = payload.enabled
    rule.priority = payload.priority
    db.commit()
    db.refresh(rule)
    return AutomationRuleOut.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: int, user: CurrentUser, db: Session = Depends(get_db)
) -> Response:
    rule = _owned_rule(db, rule_id, user.tenant_id)
    db.delete(rule)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)