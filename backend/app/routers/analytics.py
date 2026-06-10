"""Analytics router — per-job aggregate metrics for the dashboard charts."""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Candidate, CandidateStage, Job, ScoreStatus
from app.schemas import AnalyticsOut

router = APIRouter(prefix="/jobs", tags=["analytics"])


@router.get("/{job_id}/analytics", response_model=AnalyticsOut)
def job_analytics(job_id: int, db: Session = Depends(get_db)) -> AnalyticsOut:
    if db.get(Job, job_id) is None:
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
    )
