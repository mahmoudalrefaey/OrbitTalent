"""Pydantic schemas: API request/response models and LLM structured-output models."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import CandidateStage, JobStatus, RejectionReason, ScoreStatus


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    tenant_id: int
    created_at: datetime


# --------------------------------------------------------------------------- #
# LLM structured-output schemas (used with client.messages.parse)
# --------------------------------------------------------------------------- #
class ScoringCriteriaLLM(BaseModel):
    """What Claude extracts from a pasted job description."""

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_years: int = 0
    must_haves: list[str] = Field(default_factory=list)


class CandidateScoreLLM(BaseModel):
    """Deep-score result for a single CV (Tier 3).

    V2: also extracts ATS profile fields in the SAME call (no extra LLM cost).
    All profile fields are optional — the model returns null when a CV doesn't
    state them, and recruiters can correct them manually.
    """

    overall_score: float = Field(ge=1, le=10)
    job_match_pct: float = Field(ge=0, le=100)
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    reasoning: str = ""
    # Enrichment (V2).
    country: str | None = None
    city: str | None = None
    experience_years: float | None = None
    education: str | None = None
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    expected_salary: int | None = None


class QuickScoreLLM(BaseModel):
    """Tier-2 cheap score. `confidence` is the model's self-reported certainty;
    above `tier2_accept_confidence` we keep this score and skip the deep call."""

    match_pct: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    top_gaps: list[str] = Field(default_factory=list, max_length=5)
    summary: str = ""


# --------------------------------------------------------------------------- #
# Criteria (API)
# --------------------------------------------------------------------------- #
class CriteriaBase(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_years: int = 0
    must_haves: list[str] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)
    # Hiring rules (V2) — all optional, additive.
    geo_allow: list[str] = Field(default_factory=list)
    geo_block: list[str] = Field(default_factory=list)
    min_degree: str | None = None
    preferred_universities: list[str] = Field(default_factory=list)
    min_experience: int | None = None
    max_experience: int | None = None
    ranking_weights: dict[str, float] = Field(default_factory=dict)


class CriteriaOut(CriteriaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int


# --------------------------------------------------------------------------- #
# Job (API)
# --------------------------------------------------------------------------- #
class JobCreate(BaseModel):
    title: str
    jd_text: str = ""


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    jd_text: str
    status: JobStatus
    created_at: datetime
    candidate_count: int = 0


class JobDetailOut(JobOut):
    criteria: CriteriaOut | None = None


class ExtractCriteriaRequest(BaseModel):
    """Optionally override the stored JD text when extracting."""

    jd_text: str | None = None


# --------------------------------------------------------------------------- #
# Candidate (API)
# --------------------------------------------------------------------------- #
class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    filename: str
    ats_score: float | None
    job_match_pct: float | None
    overall_score: float | None
    ats_issues: list[str]
    matched_keywords: list[str]
    missing_keywords: list[str]
    reasoning: str
    stage: CandidateStage
    rejection_reason: RejectionReason | None = None
    assigned_recruiter_id: int | None = None
    score_status: ScoreStatus
    error: str
    created_at: datetime
    applied_at: datetime | None = None
    # ATS profile (V2).
    country: str | None = None
    city: str | None = None
    experience_years: float | None = None
    education: str | None = None
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    expected_salary: int | None = None


class CandidateDetailOut(CandidateOut):
    parsed_text: str


class StageUpdate(BaseModel):
    stage: CandidateStage
    reason: str = ""
    rejection_reason: RejectionReason | None = None


class CandidatePatch(BaseModel):
    """Partial edit of a candidate's editable fields. All optional."""

    stage: CandidateStage | None = None
    rejection_reason: RejectionReason | None = None
    assigned_recruiter_id: int | None = None
    country: str | None = None
    city: str | None = None
    experience_years: float | None = None
    education: str | None = None
    certifications: list[str] | None = None
    languages: list[str] | None = None
    expected_salary: int | None = None


class BulkAction(BaseModel):
    """Apply one action to many candidates (tenant-checked)."""

    candidate_ids: list[int] = Field(min_length=1)
    action: str  # move_stage | reject | shortlist | export
    stage: CandidateStage | None = None          # for move_stage
    rejection_reason: RejectionReason | None = None  # for reject
    reason: str = ""


class StageEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    from_stage: CandidateStage | None
    to_stage: CandidateStage
    reason: str
    by_user_id: int | None
    at: datetime


class CandidateSearchRequest(BaseModel):
    """Structured + free-text candidate search (tenant-scoped)."""

    query: str = ""                       # free-text → BM25 ranking
    job_id: int | None = None
    skills: list[str] = Field(default_factory=list)
    country: str | None = None
    city: str | None = None
    min_experience: float | None = None
    max_experience: float | None = None
    education: str | None = None
    min_score: float | None = None
    max_score: float | None = None
    stage: CandidateStage | None = None
    applied_after: datetime | None = None
    applied_before: datetime | None = None
    max_salary: int | None = None
    languages: list[str] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class CandidateSearchResult(BaseModel):
    total: int
    results: list[CandidateOut]


# --------------------------------------------------------------------------- #
# Automation rules (API)
# --------------------------------------------------------------------------- #
class AutomationRuleBase(BaseModel):
    name: str = ""
    job_id: int | None = None
    trigger_json: list[dict] = Field(default_factory=list)
    action_json: dict = Field(default_factory=dict)
    enabled: bool = True
    priority: int = 0


class AutomationRuleOut(AutomationRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --------------------------------------------------------------------------- #
# Analytics (API)
# --------------------------------------------------------------------------- #
class SkillGap(BaseModel):
    keyword: str
    count: int                      # candidates missing this skill
    pct: float                      # share of candidates missing it (0-100)
    example_candidate_ids: list[int] = Field(default_factory=list)


class FunnelStage(BaseModel):
    stage: str
    count: int                      # candidates that ever reached this stage
    conversion_from_prev: float | None = None  # % of prev stage that advanced


class AnalyticsOut(BaseModel):
    job_id: int
    total: int
    scored: int
    pending: int
    filtered_out: int
    failed: int
    avg_overall_score: float | None
    avg_ats_score: float | None
    avg_job_match_pct: float | None
    stage_counts: dict[str, int]
    # Top missing skills — richer (count + pct + example candidates).
    top_missing_keywords: list[dict]  # legacy [{"keyword","count"}] kept for compat
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    # Funnel + conversions (from stage_events history).
    funnel: list[FunnelStage] = Field(default_factory=list)
    # AI score distribution — histogram buckets of overall_score (1-10).
    score_distribution: dict[str, int] = Field(default_factory=dict)  # {"1-2": n, ...}
    # Geography aggregates.
    by_country: dict[str, int] = Field(default_factory=dict)
    by_city: dict[str, int] = Field(default_factory=dict)
    # Rejection analytics.
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
    # Cascade efficiency metrics.
    tier_distribution: dict[str, int] = Field(default_factory=dict)  # {"0": n, "1": n, "2": n, "3": n}
    cache_hit_rate: float = 0.0  # 0-1, share of candidates that hit any cache
    est_total_cost_usd: float = 0.0


class JobSummary(BaseModel):
    id: int
    title: str
    status: JobStatus
    total_candidates: int
    hired: int
    rejected: int
    avg_overall_score: float | None


class OverviewOut(BaseModel):
    """Org-wide (tenant) dashboard rollup across all jobs."""

    total_jobs: int
    active_jobs: int
    total_candidates: int
    total_hired: int
    total_rejected: int
    avg_overall_score: float | None
    top_missing_skills: list[SkillGap] = Field(default_factory=list)
    by_country: dict[str, int] = Field(default_factory=dict)
    jobs: list[JobSummary] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
class HealthOut(BaseModel):
    status: str
    llm_enabled: bool
    provider: str
