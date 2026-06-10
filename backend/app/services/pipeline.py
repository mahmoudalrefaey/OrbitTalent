"""Per-CV scoring pipeline orchestration.

Flow for one candidate (see plan):
  parse -> ATS score -> keyword match -> cheap pre-filter gate -> deep score.

Deterministic steps always run. LLM steps run only when an LLMService is
provided (i.e. an API key is configured); without it, candidates keep their
ATS + keyword results and are left in `pending` deep-score state so the value
of the deterministic layer is still visible.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Candidate, Job, ScoreStatus
from app.services import keyword_matcher, llm
from app.services.ats_scorer import score_ats
from app.services.cv_parser import parse_cv


def _all_keywords(job: Job) -> list[str]:
    c = job.criteria
    if c is None:
        return []
    # required + preferred + must_haves, de-duplicated, order preserved.
    seen: dict[str, None] = {}
    for kw in (*c.required_skills, *c.preferred_skills, *c.must_haves):
        if kw and kw.strip():
            seen.setdefault(kw, None)
    return list(seen)


def process_candidate(
    db: Session,
    candidate_id: int,
    file_bytes: bytes,
    llm_service: llm.LLMService | None,
) -> None:
    """Run the full pipeline for one candidate and persist results.

    Safe to call in a background task: it opens nothing it doesn't close and
    records failures on the row rather than raising.
    """
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        return

    candidate.score_status = ScoreStatus.processing
    db.commit()

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
            candidate.reasoning = (
                "Deterministic scoring complete. Configure ANTHROPIC_API_KEY for "
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

        # 4. Cheap pre-filter gate.
        gate = llm_service.prefilter(summary, parsed.text)
        if not gate.relevant:
            candidate.score_status = ScoreStatus.filtered_out
            candidate.overall_score = 1.0
            candidate.job_match_pct = 0.0
            candidate.reasoning = f"Filtered out at pre-screen: {gate.reason}"
            db.commit()
            return

        # 5. Deep score (Opus).
        score = llm_service.deep_score(summary, parsed.text)
        candidate.overall_score = score.overall_score
        candidate.job_match_pct = score.job_match_pct
        candidate.reasoning = score.reasoning
        # Merge LLM-found keywords with deterministic matches (union).
        if score.matched_keywords:
            candidate.matched_keywords = sorted(
                set(candidate.matched_keywords) | set(score.matched_keywords)
            )
        if score.missing_keywords:
            candidate.missing_keywords = score.missing_keywords
        candidate.score_status = ScoreStatus.scored
        db.commit()

    except Exception as exc:  # noqa: BLE001 — one bad CV must not sink the batch
        db.rollback()
        fresh = db.get(Candidate, candidate_id)
        if fresh is not None:
            fresh.score_status = ScoreStatus.failed
            fresh.error = f"{type(exc).__name__}: {exc}"
            db.commit()
