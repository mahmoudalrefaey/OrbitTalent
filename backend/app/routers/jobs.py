"""Jobs router — create/list/get jobs, extract & edit scoring criteria."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    DEFAULT_TENANT_ID,
    Candidate,
    Job,
    JobStatus,
    ScoringCriteria,
)
from app.schemas import (
    CriteriaBase,
    CriteriaOut,
    ExtractCriteriaRequest,
    JobCreate,
    JobDetailOut,
    JobOut,
)
from app.services import llm

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _to_job_out(db: Session, job: Job) -> JobOut:
    from sqlalchemy import func

    total = (
        db.scalar(select(func.count(Candidate.id)).where(Candidate.job_id == job.id))
        or 0
    )
    return JobOut(
        id=job.id,
        title=job.title,
        jd_text=job.jd_text,
        status=job.status,
        created_at=job.created_at,
        candidate_count=total,
    )


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> JobOut:
    job = Job(
        tenant_id=DEFAULT_TENANT_ID,
        title=payload.title,
        jd_text=payload.jd_text,
        status=JobStatus.draft,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _to_job_out(db, job)


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)) -> list[JobOut]:
    jobs = db.scalars(select(Job).order_by(Job.created_at.desc())).all()
    return [_to_job_out(db, j) for j in jobs]


@router.get("/{job_id}", response_model=JobDetailOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobDetailOut:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    base = _to_job_out(db, job).model_dump()
    crit = job.criteria
    base["criteria"] = CriteriaOut.model_validate(crit) if crit else None
    return JobDetailOut(**base)


@router.post("/{job_id}/extract-criteria", response_model=CriteriaOut)
def extract_criteria(
    job_id: int,
    payload: ExtractCriteriaRequest,
    db: Session = Depends(get_db),
) -> CriteriaOut:
    """Call Claude to extract structured criteria from the JD."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")

    jd = payload.jd_text if payload.jd_text is not None else job.jd_text
    if not jd.strip():
        raise HTTPException(400, "Job description is empty")

    try:
        service = llm.get_llm_service()
    except llm.LLMUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc

    extracted = service.extract_criteria(jd)

    crit = job.criteria
    if crit is None:
        crit = ScoringCriteria(job_id=job.id)
        db.add(crit)
    crit.required_skills = extracted.required_skills
    crit.preferred_skills = extracted.preferred_skills
    crit.min_years = extracted.min_years
    crit.must_haves = extracted.must_haves
    # Sensible default weights (HR can edit).
    crit.weights = {
        "required_skills": 0.5,
        "preferred_skills": 0.2,
        "min_years": 0.15,
        "must_haves": 0.15,
    }
    # Persist updated JD if provided.
    if payload.jd_text is not None:
        job.jd_text = payload.jd_text
    db.commit()
    db.refresh(crit)
    return CriteriaOut.model_validate(crit)


@router.put("/{job_id}/criteria", response_model=CriteriaOut)
def update_criteria(
    job_id: int, payload: CriteriaBase, db: Session = Depends(get_db)
) -> CriteriaOut:
    """HR-edited criteria (after reviewing extraction)."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")

    crit = job.criteria
    if crit is None:
        crit = ScoringCriteria(job_id=job.id)
        db.add(crit)
    crit.required_skills = payload.required_skills
    crit.preferred_skills = payload.preferred_skills
    crit.min_years = payload.min_years
    crit.must_haves = payload.must_haves
    crit.weights = payload.weights or {
        "required_skills": 0.5,
        "preferred_skills": 0.2,
        "min_years": 0.15,
        "must_haves": 0.15,
    }
    # Confirming criteria flips the job to 'ready' to accept CVs.
    job.status = JobStatus.ready
    db.commit()
    db.refresh(crit)
    return CriteriaOut.model_validate(crit)
