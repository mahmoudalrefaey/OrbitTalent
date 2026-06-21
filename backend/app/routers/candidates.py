"""Candidates router — upload CVs, list/rank, detail, stage updates."""
from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.deps import CurrentUser
from app.models import (
    Candidate,
    Job,
    ScoreStatus,
)
from app.schemas import (
    CandidateDetailOut,
    CandidateOut,
    StageUpdate,
)
from app.services import llm
from app.services.pipeline import process_candidate

router = APIRouter(tags=["candidates"])


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


def _run_pipeline_bg(
    candidate_id: int,
    file_bytes: bytes,
    job_embedding: list[float] | None = None,
) -> None:
    """Background task entry — opens its own DB session and LLM service."""
    service: llm.LLMService | None
    try:
        service = llm.get_llm_service()
    except llm.LLMUnavailableError:
        service = None

    with SessionLocal() as db:
        process_candidate(db, candidate_id, file_bytes, service, job_embedding)


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

    # Precompute the job-criteria embedding ONCE per batch (Tier-1 gate). Cheap
    # and shared across every CV in the upload. Skips silently if embeddings
    # are disabled/unsupported.
    job_embedding = _job_embedding(db, job)

    created: list[Candidate] = []
    for upload in files:
        data = await upload.read()
        candidate = Candidate(
            job_id=job.id,
            tenant_id=user.tenant_id,
            filename=upload.filename or "untitled",
            score_status=ScoreStatus.pending,
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        # Capture bytes by value so the task isn't tied to the request lifecycle.
        background.add_task(_run_pipeline_bg, candidate.id, data, job_embedding)
        created.append(candidate)

    return [CandidateOut.model_validate(c) for c in created]


def _job_embedding(db: Session, job: Job) -> list[float] | None:
    """Embed the job criteria once for the Tier-1 similarity gate.

    Returns None when embeddings are disabled, unsupported, or no LLM key is
    configured — the cascade then skips Tier 1 entirely.
    """
    crit = job.criteria
    if crit is None:
        return None
    try:
        service = llm.get_llm_service()
    except llm.LLMUnavailableError:
        return None
    embed = getattr(service, "embed", None)
    if embed is None:
        return None
    summary = llm.criteria_summary(
        crit.required_skills,
        crit.preferred_skills,
        crit.min_years,
        crit.must_haves,
        crit.weights,
    )
    return embed(summary, db=db, tenant_id=job.tenant_id)


@router.get("/jobs/{job_id}/candidates", response_model=list[CandidateOut])
def list_candidates(
    job_id: int, user: CurrentUser, db: Session = Depends(get_db)
) -> list[CandidateOut]:
    _owned_job(db, job_id, user.tenant_id)
    rows = db.scalars(
        select(Candidate)
        .where(Candidate.job_id == job_id)
        # Highest overall score first; nulls (still processing) last.
        .order_by(
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
    candidate.stage = payload.stage
    db.commit()
    db.refresh(candidate)
    return CandidateOut.model_validate(candidate)
