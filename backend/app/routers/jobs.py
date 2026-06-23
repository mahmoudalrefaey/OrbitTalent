"""Jobs router — create/list/get jobs, extract & edit scoring criteria."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser
from app.models import (
    AutomationRule,
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


def _get_owned_job(db: Session, job_id: int, tenant_id: int) -> Job:
    """Fetch a job that belongs to the caller's tenant, or 404.

    Using 404 (not 403) for cross-tenant access avoids leaking the existence
    of other tenants' jobs (IDOR-safe).
    """
    job = db.get(Job, job_id)
    if job is None or job.tenant_id != tenant_id:
        raise HTTPException(404, "Job not found")
    return job


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
def create_job(
    payload: JobCreate, user: CurrentUser, db: Session = Depends(get_db)
) -> JobOut:
    job = Job(
        tenant_id=user.tenant_id,
        title=payload.title,
        jd_text=payload.jd_text,
        status=JobStatus.draft,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _to_job_out(db, job)


@router.get("", response_model=list[JobOut])
def list_jobs(user: CurrentUser, db: Session = Depends(get_db)) -> list[JobOut]:
    jobs = db.scalars(
        select(Job)
        .where(Job.tenant_id == user.tenant_id)
        .order_by(Job.created_at.desc())
    ).all()
    return [_to_job_out(db, j) for j in jobs]


@router.get("/{job_id}", response_model=JobDetailOut)
def get_job(
    job_id: int, user: CurrentUser, db: Session = Depends(get_db)
) -> JobDetailOut:
    job = _get_owned_job(db, job_id, user.tenant_id)
    base = _to_job_out(db, job).model_dump()
    crit = job.criteria
    base["criteria"] = CriteriaOut.model_validate(crit) if crit else None
    return JobDetailOut(**base)


@router.post("/{job_id}/extract-criteria", response_model=CriteriaOut)
def extract_criteria(
    job_id: int,
    payload: ExtractCriteriaRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> CriteriaOut:
    """Call the LLM to extract structured criteria from the JD."""
    job = _get_owned_job(db, job_id, user.tenant_id)

    jd = payload.jd_text if payload.jd_text is not None else job.jd_text
    if not jd.strip():
        raise HTTPException(400, "Job description is empty")

    try:
        service = llm.get_llm_service()
    except llm.LLMUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc

    extracted = service.extract_criteria(jd, db=db, tenant_id=user.tenant_id)

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
    job_id: int,
    payload: CriteriaBase,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> CriteriaOut:
    """HR-edited criteria (after reviewing extraction)."""
    job = _get_owned_job(db, job_id, user.tenant_id)

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
    # Hiring rules (V2).
    crit.geo_allow = payload.geo_allow
    crit.geo_block = payload.geo_block
    crit.min_degree = payload.min_degree
    crit.preferred_universities = payload.preferred_universities
    crit.min_experience = payload.min_experience
    crit.max_experience = payload.max_experience
    crit.ranking_weights = payload.ranking_weights
    # Confirming criteria flips the job to 'ready' to accept CVs.
    job.status = JobStatus.ready
    db.commit()
    db.refresh(crit)
    return CriteriaOut.model_validate(crit)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int, user: CurrentUser, db: Session = Depends(get_db)
) -> Response:
    """Delete a job and everything attached to it.

    The ORM relationships cascade-delete the criteria, candidates, and each
    candidate's stage-event history. Automation rules scoped to this job have no
    cascade relationship, so they are removed explicitly first.
    """
    job = _get_owned_job(db, job_id, user.tenant_id)
    db.execute(delete(AutomationRule).where(AutomationRule.job_id == job_id))
    db.delete(job)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
