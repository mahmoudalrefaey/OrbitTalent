"""Candidate stage transitions + history.

Single choke-point for changing a candidate's stage so that EVERY change —
manual, bulk, or automation — appends a `StageEvent`. The event history powers
funnel, conversion, time-in-stage, and recruiter-response analytics.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Candidate, CandidateStage, RejectionReason, StageEvent


def change_stage(
    db: Session,
    candidate: Candidate,
    to_stage: CandidateStage,
    *,
    by_user_id: int | None = None,
    reason: str = "",
    rejection_reason: RejectionReason | None = None,
    commit: bool = True,
) -> Candidate:
    """Move a candidate to `to_stage` and record a StageEvent.

    No-ops (records no event) if the stage is unchanged. Clears
    rejection_reason when moving away from `rejected`.
    """
    from_stage = candidate.stage
    if from_stage == to_stage and (
        rejection_reason is None or candidate.rejection_reason == rejection_reason
    ):
        return candidate

    candidate.stage = to_stage
    if to_stage == CandidateStage.rejected:
        candidate.rejection_reason = rejection_reason
    else:
        candidate.rejection_reason = None

    db.add(
        StageEvent(
            tenant_id=candidate.tenant_id,
            candidate_id=candidate.id,
            from_stage=from_stage,
            to_stage=to_stage,
            reason=reason,
            by_user_id=by_user_id,
        )
    )
    if commit:
        db.commit()
        db.refresh(candidate)
    return candidate


def record_initial_stage(db: Session, candidate: Candidate, *, commit: bool = True) -> None:
    """Append the seed StageEvent (from_stage=None -> current stage) for a new
    candidate, so the funnel counts it as having entered the pipeline."""
    db.add(
        StageEvent(
            tenant_id=candidate.tenant_id,
            candidate_id=candidate.id,
            from_stage=None,
            to_stage=candidate.stage,
            reason="applied",
        )
    )
    if commit:
        db.commit()
