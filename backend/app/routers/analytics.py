"""Analytics router: per-job metrics, the global overview, and CSV export."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser
from app.models import (
    Candidate,
    CandidateStage,
    Job,
    JobStatus,
    ScoreStatus,
    StageEvent,
)
from app.schemas import AnalyticsOut, JobSummary, OverviewOut
from app.services import analytics_service as A

router = APIRouter(tags=["analytics"])


def _avg(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


@router.get("/jobs/{job_id}/analytics", response_model=AnalyticsOut)
def job_analytics(
    job_id: int, user: CurrentUser, db: Session = Depends(get_db)
) -> AnalyticsOut:
    job = db.get(Job, job_id)
    if job is None or job.tenant_id != user.tenant_id:
        raise HTTPException(404, "Job not found")

    rows = db.scalars(select(Candidate).where(Candidate.job_id == job_id)).all()
    total = len(rows)

    def status_count(s: ScoreStatus) -> int:
        return sum(1 for r in rows if r.score_status == s)

    stage_counts = {stage.value: 0 for stage in CandidateStage}
    for r in rows:
        stage_counts[r.stage.value] += 1

    gaps = A.skill_gaps(rows)
    # Legacy shape kept for any old client.
    top_missing = [{"keyword": g.keyword, "count": g.count} for g in gaps[:10]]

    events = db.scalars(
        select(StageEvent).where(StageEvent.candidate_id.in_([r.id for r in rows]))
    ).all() if rows else []

    by_country, by_city = A.geography(rows)

    tier_distribution: dict[str, int] = {"0": 0, "1": 0, "2": 0, "3": 0}
    for r in rows:
        key = str(r.tier_reached if r.tier_reached is not None else 0)
        tier_distribution[key] = tier_distribution.get(key, 0) + 1
    cache_hits = sum(1 for r in rows if r.cache_hit)

    return AnalyticsOut(
        job_id=job_id,
        total=total,
        scored=status_count(ScoreStatus.scored),
        pending=status_count(ScoreStatus.pending) + status_count(ScoreStatus.processing),
        filtered_out=status_count(ScoreStatus.filtered_out),
        failed=status_count(ScoreStatus.failed),
        avg_overall_score=_avg([r.overall_score for r in rows]),
        avg_ats_score=_avg([r.ats_score for r in rows]),
        avg_job_match_pct=_avg([r.job_match_pct for r in rows]),
        stage_counts=stage_counts,
        top_missing_keywords=top_missing,
        skill_gaps=gaps,
        funnel=A.funnel(events),
        score_distribution=A.score_distribution(rows),
        by_country=by_country,
        by_city=by_city,
        rejection_reasons=A.rejection_breakdown(rows),
        tier_distribution=tier_distribution,
        cache_hit_rate=round(cache_hits / total, 3) if total else 0.0,
        est_total_cost_usd=round(sum(r.est_cost_usd or 0.0 for r in rows), 4),
    )


@router.get("/jobs/{job_id}/analytics/export", response_class=PlainTextResponse)
def export_candidates_csv(
    job_id: int, user: CurrentUser, db: Session = Depends(get_db)
) -> PlainTextResponse:
    job = db.get(Job, job_id)
    if job is None or job.tenant_id != user.tenant_id:
        raise HTTPException(404, "Job not found")
    rows = db.scalars(select(Candidate).where(Candidate.job_id == job_id)).all()
    csv_text = A.candidates_to_csv(rows)
    return PlainTextResponse(
        csv_text,
        headers={
            "Content-Disposition": f'attachment; filename="job-{job_id}-candidates.csv"'
        },
        media_type="text/csv",
    )


@router.get("/analytics/overview", response_model=OverviewOut)
def overview(user: CurrentUser, db: Session = Depends(get_db)) -> OverviewOut:
    """Org-wide rollup across all the tenant's jobs."""
    jobs = db.scalars(select(Job).where(Job.tenant_id == user.tenant_id)).all()
    cands = db.scalars(
        select(Candidate).where(Candidate.tenant_id == user.tenant_id)
    ).all()

    by_job: dict[int, list[Candidate]] = {}
    for c in cands:
        by_job.setdefault(c.job_id, []).append(c)

    job_summaries: list[JobSummary] = []
    for j in jobs:
        jc = by_job.get(j.id, [])
        job_summaries.append(
            JobSummary(
                id=j.id,
                title=j.title,
                status=j.status,
                total_candidates=len(jc),
                hired=sum(1 for c in jc if c.stage == CandidateStage.hired),
                rejected=sum(1 for c in jc if c.stage == CandidateStage.rejected),
                avg_overall_score=_avg([c.overall_score for c in jc]),
            )
        )

    by_country, _ = A.geography(cands)

    return OverviewOut(
        total_jobs=len(jobs),
        active_jobs=sum(1 for j in jobs if j.status != JobStatus.archived),
        total_candidates=len(cands),
        total_hired=sum(1 for c in cands if c.stage == CandidateStage.hired),
        total_rejected=sum(1 for c in cands if c.stage == CandidateStage.rejected),
        avg_overall_score=_avg([c.overall_score for c in cands]),
        top_missing_skills=A.skill_gaps(cands, top=15),
        by_country=by_country,
        jobs=job_summaries,
    )
