"""Search + comparison router.

Structured candidate search with optional free-text ranking via the
deterministic BM25 similarity engine (no embeddings). Tenant-scoped.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser
from app.models import Candidate
from app.schemas import (
    CandidateOut,
    CandidateSearchRequest,
    CandidateSearchResult,
)
from app.services import similarity

router = APIRouter(tags=["search"])


@router.post("/candidates/search", response_model=CandidateSearchResult)
def search_candidates(
    payload: CandidateSearchRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> CandidateSearchResult:
    q = select(Candidate).where(Candidate.tenant_id == user.tenant_id)

    if payload.job_id is not None:
        q = q.where(Candidate.job_id == payload.job_id)
    if payload.country:
        q = q.where(Candidate.country == payload.country)
    if payload.city:
        q = q.where(Candidate.city == payload.city)
    if payload.education:
        q = q.where(Candidate.education.ilike(f"%{payload.education}%"))
    if payload.stage is not None:
        q = q.where(Candidate.stage == payload.stage)
    if payload.min_experience is not None:
        q = q.where(Candidate.experience_years >= payload.min_experience)
    if payload.max_experience is not None:
        q = q.where(Candidate.experience_years <= payload.max_experience)
    if payload.min_score is not None:
        q = q.where(Candidate.overall_score >= payload.min_score)
    if payload.max_score is not None:
        q = q.where(Candidate.overall_score <= payload.max_score)
    if payload.max_salary is not None:
        q = q.where(Candidate.expected_salary <= payload.max_salary)
    if payload.applied_after is not None:
        q = q.where(Candidate.applied_at >= payload.applied_after)
    if payload.applied_before is not None:
        q = q.where(Candidate.applied_at <= payload.applied_before)

    rows = list(db.scalars(q).all())

    # Skill filter (post-query; uses keyword matcher via similarity helpers).
    if payload.skills:
        from app.services import keyword_matcher

        def has_all(c: Candidate) -> bool:
            km = keyword_matcher.match_keywords(c.parsed_text or "", payload.skills)
            return len(km.matched) == len(payload.skills)

        rows = [c for c in rows if has_all(c)]
    if payload.languages:
        wanted = {x.lower() for x in payload.languages}
        rows = [
            c for c in rows
            if wanted.issubset({l.lower() for l in (c.languages or [])})
        ]

    # Free-text ranking via BM25 over CV text.
    if payload.query.strip() and rows:
        scores = similarity.rank_candidates(
            payload.query, [c.parsed_text or "" for c in rows]
        )
        ranked = sorted(zip(rows, scores), key=lambda t: t[1], reverse=True)
        rows = [c for c, _ in ranked]
    else:
        rows.sort(
            key=lambda c: (c.overall_score is None, -(c.overall_score or 0))
        )

    total = len(rows)
    page = rows[payload.offset : payload.offset + payload.limit]
    return CandidateSearchResult(
        total=total,
        results=[CandidateOut.model_validate(c) for c in page],
    )


@router.get("/candidates/compare", response_model=list[CandidateOut])
def compare_candidates(
    user: CurrentUser,
    ids: str = Query(..., description="Comma-separated candidate ids (2-4)"),
    db: Session = Depends(get_db),
) -> list[CandidateOut]:
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(400, "ids must be comma-separated integers")
    if not (2 <= len(id_list) <= 4):
        raise HTTPException(400, "Compare between 2 and 4 candidates")

    rows = db.scalars(
        select(Candidate).where(
            Candidate.id.in_(id_list),
            Candidate.tenant_id == user.tenant_id,
        )
    ).all()
    # Preserve the requested order.
    by_id = {c.id: c for c in rows}
    ordered = [by_id[i] for i in id_list if i in by_id]
    return [CandidateOut.model_validate(c) for c in ordered]
