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
from app.models import (
    DEFAULT_TENANT_ID,
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
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> list[CandidateOut]:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    if not files:
        raise HTTPException(400, "No files uploaded")

    created: list[Candidate] = []
    for upload in files:
        data = await upload.read()
        candidate = Candidate(
            job_id=job.id,
            tenant_id=DEFAULT_TENANT_ID,
            filename=upload.filename or "untitled",
            score_status=ScoreStatus.pending,
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        # Capture bytes by value so the task isn't tied to the request lifecycle.
        background.add_task(_run_pipeline_bg, candidate.id, data)
        created.append(candidate)

    return [CandidateOut.model_validate(c) for c in created]


@router.get("/jobs/{job_id}/candidates", response_model=list[CandidateOut])
def list_candidates(job_id: int, db: Session = Depends(get_db)) -> list[CandidateOut]:
    if db.get(Job, job_id) is None:
        raise HTTPException(404, "Job not found")
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
def get_candidate(candidate_id: int, db: Session = Depends(get_db)) -> CandidateDetailOut:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(404, "Candidate not found")
    return CandidateDetailOut.model_validate(candidate)


@router.patch("/candidates/{candidate_id}/stage", response_model=CandidateOut)
def update_stage(
    candidate_id: int,
    payload: StageUpdate,
    db: Session = Depends(get_db),
) -> CandidateOut:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(404, "Candidate not found")
    candidate.stage = payload.stage
    db.commit()
    db.refresh(candidate)
    return CandidateOut.model_validate(candidate)
