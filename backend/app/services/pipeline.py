"""Per-CV scoring pipeline orchestration.

Flow for one candidate:
  parse -> ATS score -> keyword match -> cascade (Tier 0..3).

Deterministic steps (parse/ATS/keyword) always run. The cascade runs only when
an LLMService is provided (i.e. an API key is configured); without it,
candidates keep their ATS + keyword results and are left in `pending` so the
value of the deterministic layer is still visible.

The cascade is cost-optimized: see app.services.cascade. Per-candidate cost is
summed from the usage rows written during this candidate's run and stored on
the row for the analytics dashboard.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate, Job, ScoreStatus, UsageRecord
from app.services import cascade, keyword_matcher, llm
from app.services.ats_scorer import score_ats
from app.services.cv_parser import parse_cv


def _all_keywords(job: Job) -> list[str]:
    c = job.criteria
    if c is None:
        return []
    seen: dict[str, None] = {}
    for kw in (*c.required_skills, *c.preferred_skills, *c.must_haves):
        if kw and kw.strip():
            seen.setdefault(kw, None)
    return list(seen)


def _cost_since(db: Session, started_at: datetime) -> float:
    """Sum usage cost recorded since `started_at` (this candidate's spend)."""
    rows = db.scalars(
        select(UsageRecord).where(UsageRecord.created_at >= started_at)
    ).all()
    return round(sum(r.cost_usd for r in rows), 6)


def process_candidate(
    db: Session,
    candidate_id: int,
    file_bytes: bytes,
    llm_service: llm.LLMService | None,
    job_embedding: list[float] | None = None,
) -> None:
    """Run the full pipeline for one candidate and persist results.

    Safe to call in a background task: records failures on the row rather than
    raising. `job_embedding` may be precomputed once per batch and passed in.
    """
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        return

    candidate.score_status = ScoreStatus.processing
    db.commit()
    started_at = datetime.now(timezone.utc)

    try:
        # 1. Parse.
        parsed = parse_cv(candidate.filename, file_bytes)
        candidate.parsed_text = parsed.text

        # 2. ATS readiness (always).
        ats = score_ats(parsed)
        candidate.ats_score = ats.score
        candidate.ats_issues = ats.issues

        # 3. Keyword match (always).
        job = candidate.job
        keywords = _all_keywords(job)
        km = keyword_matcher.match_keywords(parsed.text, keywords)
        candidate.matched_keywords = km.matched
        candidate.missing_keywords = km.missing

        if parsed.parse_error:
            candidate.score_status = ScoreStatus.failed
            candidate.error = parsed.parse_error
            db.commit()
            return

        # Without an LLM, stop after the deterministic layer.
        if llm_service is None:
            candidate.score_status = ScoreStatus.pending
            candidate.tier_reached = 0
            candidate.reasoning = (
                "Deterministic scoring complete. Configure LLM_API_KEY for "
                "AI deep scoring (overall score, job-match %, reasoning)."
            )
            db.commit()
            return

        crit = job.criteria
        summary = llm.criteria_summary(
            crit.required_skills if crit else [],
            crit.preferred_skills if crit else [],
            crit.min_years if crit else 0,
            crit.must_haves if crit else [],
            crit.weights if crit else {},
        )

        # 4. Cascade (Tier 0..3).
        result = cascade.run_cascade(
            llm_service,
            criteria_summary=summary,
            required_skills=crit.required_skills if crit else [],
            cv_text=parsed.text,
            matched_keywords=km.matched,
            missing_keywords=km.missing,
            job_embedding=job_embedding,
            db=db,
            tenant_id=candidate.tenant_id,
        )

        candidate.score_status = result.status
        candidate.tier_reached = result.tier_reached
        candidate.overall_score = result.overall_score
        candidate.job_match_pct = result.job_match_pct
        candidate.reasoning = result.reasoning
        candidate.matched_keywords = result.matched_keywords
        candidate.missing_keywords = result.missing_keywords

        # 5. Cost + cache telemetry for this candidate.
        rows = db.scalars(
            select(UsageRecord).where(UsageRecord.created_at >= started_at)
        ).all()
        candidate.est_cost_usd = round(sum(r.cost_usd for r in rows), 6)
        candidate.cache_hit = any(r.cached_tokens > 0 for r in rows)
        db.commit()

    except Exception as exc:  # noqa: BLE001 — one bad CV must not sink the batch
        db.rollback()
        fresh = db.get(Candidate, candidate_id)
        if fresh is not None:
            fresh.score_status = ScoreStatus.failed
            fresh.error = f"{type(exc).__name__}: {exc}"
            db.commit()
