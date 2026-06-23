"""Cost-optimized cascade scoring.

Each candidate exits at the cheapest tier that yields a confident answer:

  Tier 0  deterministic   parse + ATS + keyword coverage         (free)
  Tier 1  similarity gate  BM25(JD, CV) + skill overlap           (free)
  Tier 2  cheap LLM        one combined prefilter+score call      (cheap)
  Tier 3  deep LLM         precise overall score                  (expensive)

Most CVs resolve at Tier 0-2; the expensive model runs only on borderline or
strong candidates. The criteria block is prompt-cached so a whole batch is
billed for it once. This module is pure orchestration logic over an
`LLMService` + the deterministic `similarity` engine; persistence lives in
`pipeline.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.config import get_settings
from app.models import DEFAULT_TENANT_ID, ScoreStatus
from app.services import llm as llm_mod
from app.services import similarity

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
    # Profile fields extracted by the Tier-3 deep score (empty otherwise).
    enrichment: dict = field(default_factory=dict)


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
    preferred_skills: list[str],
    jd_text: str,
    cv_text: str,
    matched_keywords: list[str],
    missing_keywords: list[str],
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

    # ---- Tier 1: deterministic BM25 + skill similarity gate -------------
    # (Replaces the old embedding gate — g0i.ai has no embedding models.)
    # similarity is 0..100; below the threshold (×100) we reject before any
    # LLM spend. Skipped when there's no JD text to compare against.
    if jd_text.strip():
        sim = similarity.job_similarity(
            cv_text, jd_text, required_skills, preferred_skills
        )
        if sim < settings.tier1_min_similarity * 100:
            return CascadeResult(
                status=ScoreStatus.filtered_out,
                tier_reached=1,
                overall_score=1.0,
                job_match_pct=sim,
                reasoning=(
                    f"Filtered at Tier 1: low lexical similarity to the role "
                    f"({sim:.0f}/100, BM25 + skill overlap)."
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
    # Profile enrichment extracted in the same call (null fields omitted).
    enrichment = {
        k: v
        for k, v in {
            "country": deep.country,
            "city": deep.city,
            "experience_years": deep.experience_years,
            "education": deep.education,
            "certifications": deep.certifications,
            "languages": deep.languages,
            "expected_salary": deep.expected_salary,
        }.items()
        if v not in (None, [], "")
    }
    return CascadeResult(
        status=ScoreStatus.scored,
        tier_reached=3,
        overall_score=deep.overall_score,
        job_match_pct=deep.job_match_pct,
        reasoning=deep.reasoning,
        matched_keywords=matched,
        missing_keywords=missing,
        enrichment=enrichment,
    )
