"""Analytics aggregation helpers (pure-ish; take rows, return schema pieces).

Kept separate from the router so the same builders feed both per-job analytics
and the global overview, and so they're unit-testable.
"""
from __future__ import annotations

from collections import Counter

from app.models import (
    STAGE_FUNNEL_ORDER,
    Candidate,
    CandidateStage,
    StageEvent,
)
from app.schemas import FunnelStage, SkillGap

# Score buckets for the AI score distribution (overall_score is 1..10).
_SCORE_BUCKETS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)]


def skill_gaps(rows: list[Candidate], top: int = 20) -> list[SkillGap]:
    """Most-missing skills with count, % of candidates, and example ids."""
    total = len(rows)
    counter: Counter = Counter()
    examples: dict[str, list[int]] = {}
    for r in rows:
        for kw in r.missing_keywords or []:
            counter[kw] += 1
            examples.setdefault(kw, [])
            if len(examples[kw]) < 3:
                examples[kw].append(r.id)
    out = []
    for kw, n in counter.most_common(top):
        out.append(
            SkillGap(
                keyword=kw,
                count=n,
                pct=round(100 * n / total, 1) if total else 0.0,
                example_candidate_ids=examples.get(kw, []),
            )
        )
    return out


def score_distribution(rows: list[Candidate]) -> dict[str, int]:
    dist = {f"{lo}-{hi}": 0 for lo, hi in _SCORE_BUCKETS}
    for r in rows:
        s = r.overall_score
        if s is None:
            continue
        for lo, hi in _SCORE_BUCKETS:
            if lo <= s <= hi:
                dist[f"{lo}-{hi}"] += 1
                break
    return dist


def funnel(events: list[StageEvent]) -> list[FunnelStage]:
    """Funnel counts + stage→stage conversion from stage-event history.

    A candidate "reached" a stage if any event has that stage as `to_stage`.
    Conversion = reached(stage) / reached(prev stage).
    """
    reached_by_stage: dict[CandidateStage, set[int]] = {
        s: set() for s in STAGE_FUNNEL_ORDER
    }
    for e in events:
        if e.to_stage in reached_by_stage:
            reached_by_stage[e.to_stage].add(e.candidate_id)

    out: list[FunnelStage] = []
    prev_count: int | None = None
    for stage in STAGE_FUNNEL_ORDER:
        count = len(reached_by_stage[stage])
        conv = (
            round(100 * count / prev_count, 1)
            if prev_count not in (None, 0)
            else None
        )
        out.append(FunnelStage(stage=stage.value, count=count, conversion_from_prev=conv))
        prev_count = count
    return out


def geography(rows: list[Candidate]) -> tuple[dict[str, int], dict[str, int]]:
    by_country: Counter = Counter()
    by_city: Counter = Counter()
    for r in rows:
        if r.country:
            by_country[r.country] += 1
        if r.city:
            by_city[r.city] += 1
    return dict(by_country.most_common(20)), dict(by_city.most_common(20))


def rejection_breakdown(rows: list[Candidate]) -> dict[str, int]:
    c: Counter = Counter()
    for r in rows:
        if r.stage == CandidateStage.rejected and r.rejection_reason is not None:
            c[r.rejection_reason.value] += 1
    return dict(c)


def candidates_to_csv(rows: list[Candidate]) -> str:
    """Serialize candidates to CSV text (server-side export)."""
    import csv
    import io

    cols = [
        "id", "filename", "stage", "overall_score", "job_match_pct", "ats_score",
        "country", "city", "experience_years", "education", "expected_salary",
        "rejection_reason", "created_at",
    ]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for r in rows:
        w.writerow([
            r.id, r.filename, r.stage.value if r.stage else "",
            r.overall_score, r.job_match_pct, r.ats_score,
            r.country or "", r.city or "", r.experience_years or "",
            r.education or "", r.expected_salary or "",
            r.rejection_reason.value if r.rejection_reason else "",
            r.created_at.isoformat() if r.created_at else "",
        ])
    return buf.getvalue()
