"""Cost-optimized cascade scoring.

Each candidate exits at the cheapest tier that yields a confident answer:

  Tier 0  deterministic   parse + ATS + keyword coverage         (free)
  Tier 1  embedding gate   cosine(JD, CV) similarity              (cheap, optional)
  Tier 2  cheap LLM        one combined prefilter+score call      (cheap)
  Tier 3  deep LLM         precise overall score                  (expensive)

Most CVs resolve at Tier 0-2; the expensive model runs only on borderline or
strong candidates. The criteria block is prompt-cached so a whole batch is
billed for it once. This module is pure orchestration logic over an
`LLMService`; persistence lives in `pipeline.py`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.config import get_settings
from app.models import DEFAULT_TENANT_ID, ScoreStatus
from app.services import llm as llm_mod

settings = get_settings()


@dataclass
class CascadeResult:
    """Outcome of running the cascade for one candidate."""

    status: ScoreStatus
    tier_reached: int
    overall_score: float | None = None
    job_match_pct: float | None = None
    reasoning: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def required_coverage(matched: list[str], required: list[str]) -> float:
    """Share of required skills present in the CV (Tier-0 signal)."""
    req = [r for r in required if r and r.strip()]
    if not req:
        return 1.0  # no required skills => nothing to gate on
    matched_set = {m.lower() for m in matched}
    hit = sum(1 for r in req if r.lower() in matched_set)
    return hit / len(req)


def run_cascade(
    service: llm_mod.LLMService,
    *,
    criteria_summary: str,
    required_skills: list[str],
    cv_text: str,
    matched_keywords: list[str],
    missing_keywords: list[str],
    job_embedding: list[float] | None,
    db,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> CascadeResult:
    """Run tiers 0->3, stopping as early as confidence allows."""

    # ---- Tier 0: deterministic gate -------------------------------------
    coverage = required_coverage(matched_keywords, required_skills)
    if coverage < settings.tier0_min_coverage:
        return CascadeResult(
            status=ScoreStatus.filtered_out,
            tier_reached=0,
            overall_score=1.0,
            job_match_pct=round(coverage * 100, 1),
            reasoning=(
                "Filtered at Tier 0: CV matches none of the required skills "
                "(no LLM cost incurred)."
            ),
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
        )

    # ---- Tier 1: optional embedding similarity gate ---------------------
    if job_embedding is not None:
        cv_vec = service.embed(cv_text, db=db, tenant_id=tenant_id)
        if cv_vec is not None:
            sim = cosine(job_embedding, cv_vec)
            if sim < settings.tier1_min_similarity:
                return CascadeResult(
                    status=ScoreStatus.filtered_out,
                    tier_reached=1,
                    overall_score=1.0,
                    job_match_pct=round(sim * 100, 1),
                    reasoning=(
                        f"Filtered at Tier 1: low semantic similarity to the "
                        f"role ({sim:.2f})."
                    ),
                    matched_keywords=matched_keywords,
                    missing_keywords=missing_keywords,
                )

    # ---- Tier 2: cheap combined prefilter + score -----------------------
    quick = service.quick_score(criteria_summary, cv_text, db=db, tenant_id=tenant_id)
    merged_missing = sorted(set(missing_keywords) | set(quick.top_gaps))

    confident = quick.confidence >= settings.tier2_accept_confidence
    strong = quick.match_pct >= settings.tier3_escalate_match_pct
    # Accept the cheap score only when confident AND not a strong candidate
    # worth a precise overall score. Strong candidates always escalate.
    if confident and not strong:
        return CascadeResult(
            status=ScoreStatus.scored,
            tier_reached=2,
            # Approximate overall (1-10) from match% for a consistent ranking.
            overall_score=round(1 + quick.match_pct / 100 * 9, 1),
            job_match_pct=quick.match_pct,
            reasoning=quick.summary or "Scored at Tier 2 (cheap model).",
            matched_keywords=matched_keywords,
            missing_keywords=merged_missing,
        )

    # ---- Tier 3: deep score (expensive, precise) ------------------------
    deep = service.deep_score(criteria_summary, cv_text, db=db, tenant_id=tenant_id)
    matched = sorted(set(matched_keywords) | set(deep.matched_keywords))
    missing = deep.missing_keywords or merged_missing
    return CascadeResult(
        status=ScoreStatus.scored,
        tier_reached=3,
        overall_score=deep.overall_score,
        job_match_pct=deep.job_match_pct,
        reasoning=deep.reasoning,
        matched_keywords=matched,
        missing_keywords=missing,
    )
