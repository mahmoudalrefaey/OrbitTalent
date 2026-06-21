"""Analytics router — per-job aggregate metrics for the dashboard charts."""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser
from app.models import Candidate, CandidateStage, Job, ScoreStatus
from app.schemas import AnalyticsOut

router = APIRouter(prefix="/jobs", tags=["analytics"])


@router.get("/{job_id}/analytics", response_model=AnalyticsOut)
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

    def _avg(values: list[float]) -> float | None:
        vals = [v for v in values if v is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    stage_counts = {stage.value: 0 for stage in CandidateStage}
    for r in rows:
        stage_counts[r.stage.value] += 1

    missing = Counter()
    for r in rows:
        for kw in r.missing_keywords or []:
            missing[kw] += 1
    top_missing = [
        {"keyword": kw, "count": n} for kw, n in missing.most_common(10)
    ]

    # Cascade efficiency: how many candidates exited at each tier, the share
    # that hit a prompt cache, and the summed estimated cost.
    tier_distribution: dict[str, int] = {"0": 0, "1": 0, "2": 0, "3": 0}
    for r in rows:
        key = str(r.tier_reached if r.tier_reached is not None else 0)
        tier_distribution[key] = tier_distribution.get(key, 0) + 1
    cache_hits = sum(1 for r in rows if r.cache_hit)
    cache_hit_rate = round(cache_hits / total, 3) if total else 0.0
    est_total_cost = round(sum(r.est_cost_usd or 0.0 for r in rows), 4)

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
        tier_distribution=tier_distribution,
        cache_hit_rate=cache_hit_rate,
        est_total_cost_usd=est_total_cost,
    )
