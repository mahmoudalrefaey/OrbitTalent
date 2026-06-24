"""Automation rule evaluation.

Rules are JSON: a list of trigger conditions (ALL must match) + one action.
Evaluated after scoring (auto-reject / auto-progress) and at creation
(auto-assign). Each applied action goes through `candidate_service.change_stage`
so it's recorded in stage history.

Condition shape:  {"field": <name>, "op": "lt|lte|gt|gte|eq|ne|in|nin|missing_count_gte", "value": <v>}
Action shape:     {"type": "reject", "reason": "low_ai_score"}
                  {"type": "move",   "stage": "shortlisted"}
                  {"type": "assign", "recruiter_id": 5}
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AutomationRule,
    Candidate,
    CandidateStage,
    RejectionReason,
)
from app.services import candidate_service

_NUM_OPS = {
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
}


def _candidate_field(candidate: Candidate, field: str):
    return getattr(candidate, field, None)


def _condition_matches(candidate: Candidate, cond: dict) -> bool:
    field = cond.get("field")
    op = cond.get("op")
    value = cond.get("value")

    # Special op: count of missing required skills.
    if op == "missing_count_gte":
        return len(candidate.missing_keywords or []) >= int(value)

    actual = _candidate_field(candidate, field)
    if actual is None:
        return False  # can't satisfy a comparison on a missing field

    if op in _NUM_OPS:
        # The rule value may arrive as a string (from the UI form). When the
        # candidate field is numeric, coerce the rule value to a number so
        # e.g. overall_score(8.0) < "60" compares correctly.
        a, b = actual, value
        if isinstance(a, (int, float)) and not isinstance(a, bool):
            try:
                b = float(b)
            except (TypeError, ValueError):
                return False
        else:
            # Non-numeric field (e.g. country): compare as strings.
            a, b = str(a).lower(), str(b).lower()
        try:
            return _NUM_OPS[op](a, b)
        except TypeError:
            return False
    if op == "in":
        return actual in (value or [])
    if op == "nin":
        return actual not in (value or [])
    return False


def _rule_matches(candidate: Candidate, rule: AutomationRule) -> bool:
    conds = rule.trigger_json or []
    # ALL conditions must hold (AND). Empty trigger never fires (safety).
    return bool(conds) and all(_condition_matches(candidate, c) for c in conds)


_TERMINAL_STAGES = (
    CandidateStage.rejected,
    CandidateStage.hired,
    CandidateStage.withdrawn,
)


def _apply_rule(db: Session, candidate: Candidate, rule: AutomationRule) -> str | None:
    """Apply a single (already-matched) rule's action. Caller commits."""
    action = rule.action_json or {}
    atype = action.get("type")
    if atype == "reject":
        reason = action.get("reason", "recruiter_decision")
        try:
            rej = RejectionReason(reason)
        except ValueError:
            rej = RejectionReason.recruiter_decision
        candidate_service.change_stage(
            db, candidate, CandidateStage.rejected,
            reason=f"automation: {rule.name}", rejection_reason=rej, commit=False,
        )
        return f"auto-reject ({rule.name})"
    if atype == "move":
        try:
            stage = CandidateStage(action.get("stage"))
        except ValueError:
            return None
        candidate_service.change_stage(
            db, candidate, stage,
            reason=f"automation: {rule.name}", commit=False,
        )
        return f"auto-move → {stage.value} ({rule.name})"
    if atype == "assign":
        candidate.assigned_recruiter_id = action.get("recruiter_id")
        return f"auto-assign ({rule.name})"
    return None


def _enabled_rules_for(
    db: Session, tenant_id: int, job_id: int, rule_ids: list[int] | None = None
) -> list[AutomationRule]:
    """Enabled rules for a job/tenant (job-scoped or tenant-wide), priority order.

    When `rule_ids` is given, restrict to those rule ids (still tenant/enabled
    filtered) so a manual run can target specific rules.
    """
    q = select(AutomationRule).where(
        AutomationRule.tenant_id == tenant_id,
        AutomationRule.enabled.is_(True),
        (AutomationRule.job_id == job_id) | (AutomationRule.job_id.is_(None)),
    )
    if rule_ids:
        q = q.where(AutomationRule.id.in_(rule_ids))
    return list(
        db.scalars(q.order_by(AutomationRule.priority.desc(), AutomationRule.id)).all()
    )


def apply_rules(db: Session, candidate: Candidate) -> str | None:
    """Evaluate enabled rules for this candidate's job/tenant in priority order.

    Applies the FIRST matching rule's action and returns a short description,
    or None if nothing matched. Caller commits.
    """
    # Don't override a terminal decision (already rejected/hired/withdrawn).
    if candidate.stage in _TERMINAL_STAGES:
        return None

    rules = _enabled_rules_for(db, candidate.tenant_id, candidate.job_id)
    for rule in rules:
        if _rule_matches(candidate, rule):
            return _apply_rule(db, candidate, rule)
    return None


def apply_rules_to_candidates(
    db: Session,
    candidates: list[Candidate],
    *,
    tenant_id: int,
    job_id: int,
    rule_ids: list[int] | None = None,
) -> dict:
    """Manually apply enabled rules (optionally only `rule_ids`) to candidates.

    Used by the "apply rules now" action so a recruiter can run rules against
    candidates that were uploaded before the rule existed. The first matching
    rule per candidate wins. Terminal-stage candidates are skipped (we never
    override a settled decision). Caller commits.
    """
    rules = _enabled_rules_for(db, tenant_id, job_id, rule_ids)
    matched_ids: list[int] = []
    if not rules:
        return {"applied": 0, "matched_candidate_ids": []}

    for candidate in candidates:
        if candidate.stage in _TERMINAL_STAGES:
            continue
        for rule in rules:
            if _rule_matches(candidate, rule):
                _apply_rule(db, candidate, rule)
                matched_ids.append(candidate.id)
                break
    return {"applied": len(matched_ids), "matched_candidate_ids": matched_ids}
