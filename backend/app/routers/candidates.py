"""Candidates router — upload CVs, list/rank, detail, stage updates."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal, get_db
from app.deps import CurrentUser
from app.models import (
    Candidate,
    CandidateStage,
    Job,
    RejectionReason,
    ScoreStatus,
    StageEvent,
)
from app.schemas import (
    BulkAction,
    CandidateDetailOut,
    CandidateOut,
    CandidatePatch,
    StageEventOut,
    StageUpdate,
)
from app.services import candidate_service, llm
from app.services.pipeline import process_candidate

router = APIRouter(tags=["candidates"])
settings = get_settings()


def _owned_job(db: Session, job_id: int, tenant_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.tenant_id != tenant_id:
        raise HTTPException(404, "Job not found")
    return job


def _owned_candidate(db: Session, candidate_id: int, tenant_id: int) -> Candidate:
    cand = db.get(Candidate, candidate_id)
    if cand is None or cand.tenant_id != tenant_id:
        raise HTTPException(404, "Candidate not found")
    return cand


def _run_pipeline_bg(candidate_id: int, file_bytes: bytes) -> None:
    """Background task entry — opens its own DB session and LLM service."""
    service: llm.LLMService | None
    try:
        service = llm.get_llm_service()
    except llm.LLMUnavailableError:
        service = None

    with SessionLocal() as db:
        process_candidate(db, candidate_id, file_bytes, service)


@router.post(
    "/jobs/{job_id}/candidates",
    response_model=list[CandidateOut],
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_candidates(
    job_id: int,
    background: BackgroundTasks,
    user: CurrentUser,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> list[CandidateOut]:
    job = _owned_job(db, job_id, user.tenant_id)
    if not files:
        raise HTTPException(400, "No files uploaded")

    # Daily upload quota (rolling 24h, per user == per tenant). Reject the whole
    # batch if it would exceed the cap, so partial uploads don't surprise users.
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    used = (
        db.scalar(
            select(func.count(Candidate.id)).where(
                Candidate.tenant_id == user.tenant_id,
                Candidate.created_at >= since,
            )
        )
        or 0
    )
    remaining = settings.daily_upload_limit - used
    if remaining <= 0:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Daily upload limit reached ({settings.daily_upload_limit} CVs/day). "
            "Try again later.",
        )
    if len(files) > remaining:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Upload exceeds your remaining daily quota ({remaining} of "
            f"{settings.daily_upload_limit} left).",
        )

    # Size pre-pass: read + validate every file before creating any row, so an
    # oversized file rejects the batch atomically (matches the quota behavior).
    max_bytes = settings.max_upload_mb * 1024 * 1024
    validated: list[tuple[str, bytes]] = []
    for upload in files:
        data = await upload.read()
        if len(data) > max_bytes:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"{upload.filename or 'file'}: exceeds the "
                f"{settings.max_upload_mb} MB upload limit.",
            )
        validated.append((upload.filename or "untitled", data))

    created: list[Candidate] = []
    for filename, data in validated:
        candidate = Candidate(
            job_id=job.id,
            tenant_id=user.tenant_id,
            filename=filename,
            score_status=ScoreStatus.pending,
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        candidate_service.record_initial_stage(db, candidate)
        # Capture bytes by value so the task isn't tied to the request lifecycle.
        background.add_task(_run_pipeline_bg, candidate.id, data)
        created.append(candidate)

    return [CandidateOut.model_validate(c) for c in created]


@router.get("/jobs/{job_id}/candidates", response_model=list[CandidateOut])
def list_candidates(
    job_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
    stage: CandidateStage | None = None,
) -> list[CandidateOut]:
    _owned_job(db, job_id, user.tenant_id)
    q = select(Candidate).where(Candidate.job_id == job_id)
    if stage is not None:
        q = q.where(Candidate.stage == stage)
    rows = db.scalars(
        q.order_by(
            # Highest overall score first; nulls (still processing) last.
            Candidate.overall_score.is_(None).asc(),
            Candidate.overall_score.desc(),
            Candidate.job_match_pct.desc().nullslast(),
            Candidate.created_at.desc(),
        )
    ).all()
    return [CandidateOut.model_validate(c) for c in rows]


@router.get("/candidates/{candidate_id}", response_model=CandidateDetailOut)
def get_candidate(
    candidate_id: int, user: CurrentUser, db: Session = Depends(get_db)
) -> CandidateDetailOut:
    candidate = _owned_candidate(db, candidate_id, user.tenant_id)
    return CandidateDetailOut.model_validate(candidate)


@router.patch("/candidates/{candidate_id}/stage", response_model=CandidateOut)
def update_stage(
    candidate_id: int,
    payload: StageUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> CandidateOut:
    candidate = _owned_candidate(db, candidate_id, user.tenant_id)
    candidate_service.change_stage(
        db,
        candidate,
        payload.stage,
        by_user_id=user.id,
        reason=payload.reason,
        rejection_reason=payload.rejection_reason,
    )
    return CandidateOut.model_validate(candidate)


@router.patch("/candidates/{candidate_id}", response_model=CandidateOut)
def patch_candidate(
    candidate_id: int,
    payload: CandidatePatch,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> CandidateOut:
    """Edit candidate fields (profile, assignment, and/or stage). Stage changes
    go through the history-recording helper."""
    candidate = _owned_candidate(db, candidate_id, user.tenant_id)
    data = payload.model_dump(exclude_unset=True)

    # Stage (if present) is handled via the helper so it logs a StageEvent.
    new_stage = data.pop("stage", None)
    rejection = data.pop("rejection_reason", None)

    # Validate recruiter assignment stays within the tenant.
    if "assigned_recruiter_id" in data and data["assigned_recruiter_id"] is not None:
        from app.models import User

        rec = db.get(User, data["assigned_recruiter_id"])
        if rec is None or rec.tenant_id != user.tenant_id:
            raise HTTPException(400, "Invalid recruiter")

    for k, v in data.items():
        setattr(candidate, k, v)

    if new_stage is not None:
        candidate_service.change_stage(
            db, candidate, new_stage, by_user_id=user.id,
            rejection_reason=rejection, commit=False,
        )
    elif rejection is not None:
        candidate.rejection_reason = rejection

    db.commit()
    db.refresh(candidate)
    return CandidateOut.model_validate(candidate)


@router.get("/candidates/{candidate_id}/history", response_model=list[StageEventOut])
def candidate_history(
    candidate_id: int, user: CurrentUser, db: Session = Depends(get_db)
) -> list[StageEventOut]:
    candidate = _owned_candidate(db, candidate_id, user.tenant_id)
    events = db.scalars(
        select(StageEvent)
        .where(StageEvent.candidate_id == candidate.id)
        .order_by(StageEvent.at)
    ).all()
    return [StageEventOut.model_validate(e) for e in events]


@router.post("/candidates/bulk")
def bulk_action(
    payload: BulkAction, user: CurrentUser, db: Session = Depends(get_db)
) -> dict:
    """Apply one action to many candidates (all tenant-checked).

    Actions: move_stage (needs `stage`), reject (needs `rejection_reason`),
    shortlist, export (returns the candidates as rows for client-side CSV).
    """
    rows = db.scalars(
        select(Candidate).where(
            Candidate.id.in_(payload.candidate_ids),
            Candidate.tenant_id == user.tenant_id,
        )
    ).all()
    found_ids = {c.id for c in rows}
    missing = [i for i in payload.candidate_ids if i not in found_ids]

    if payload.action == "export":
        return {
            "action": "export",
            "candidates": [CandidateOut.model_validate(c).model_dump() for c in rows],
            "skipped": missing,
        }

    if payload.action == "move_stage":
        if payload.stage is None:
            raise HTTPException(400, "move_stage requires `stage`")
        target, rej = payload.stage, None
    elif payload.action == "shortlist":
        target, rej = CandidateStage.shortlisted, None
    elif payload.action == "reject":
        target = CandidateStage.rejected
        rej = payload.rejection_reason or RejectionReason.recruiter_decision
    else:
        raise HTTPException(400, f"Unknown action: {payload.action}")

    for c in rows:
        candidate_service.change_stage(
            db, c, target, by_user_id=user.id,
            reason=payload.reason, rejection_reason=rej, commit=False,
        )
    db.commit()
    return {"action": payload.action, "updated": len(rows), "skipped": missing}
