"""Pydantic schemas: API request/response models and LLM structured-output models."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import CandidateStage, JobStatus, ScoreStatus


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
    """Deep-score result from Claude for a single CV."""

    overall_score: float = Field(ge=1, le=10)
    job_match_pct: float = Field(ge=0, le=100)
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    reasoning: str = ""


class PreFilterLLM(BaseModel):
    """Cheap relevance gate result.

    DEPRECATED: kept on the LLMService Protocol for backwards-compat but the
    new cascade pipeline does not call it. Tier 1 (embedding similarity) and
    Tier 2 (quick_score) jointly replace it with stronger signal at lower cost.
    """

    relevant: bool
    reason: str = ""


class QuickScoreLLM(BaseModel):
    """Tier-2 cheap structured score. One small LLM call.

    confidence is the model's own self-reported certainty. When >= 0.75 we
    accept the cheap score and skip the deep Tier-3 call entirely.
    """

    match_pct: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    top_gaps: list[str] = Field(default_factory=list, max_length=5)
    summary: str = ""  # one sentence, used as `reasoning` for Tier-2-only exits


# --------------------------------------------------------------------------- #
# Criteria (API)
# --------------------------------------------------------------------------- #
class CriteriaBase(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_years: int = 0
    must_haves: list[str] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)


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
    score_status: ScoreStatus
    error: str
    created_at: datetime


class CandidateDetailOut(CandidateOut):
    parsed_text: str


class StageUpdate(BaseModel):
    stage: CandidateStage


# --------------------------------------------------------------------------- #
# Analytics (API)
# --------------------------------------------------------------------------- #
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
    top_missing_keywords: list[dict]  # [{"keyword": str, "count": int}]
    # Cascade efficiency metrics.
    tier_distribution: dict[str, int] = Field(default_factory=dict)  # {"0": n, "1": n, "2": n, "3": n}
    cache_hit_rate: float = 0.0  # 0-1, share of candidates that hit any cache
    est_total_cost_usd: float = 0.0


# --------------------------------------------------------------------------- #
# Usage tracking (API)
# --------------------------------------------------------------------------- #
class UsagePerDay(BaseModel):
    date: str   # YYYY-MM-DD
    cost_usd: float
    calls: int
    cached_tokens: int
    prompt_tokens: int
    completion_tokens: int


class UsageOut(BaseModel):
    provider: str
    today_cost_usd: float
    last_7_days_cost_usd: float
    total_calls: int
    cache_hit_rate: float
    by_day: list[UsagePerDay]
    by_tier: dict[str, int]   # {"tier_0": n, ...}
    by_model: dict[str, int]


# --------------------------------------------------------------------------- #
# Health (extended)
# --------------------------------------------------------------------------- #
class HealthOut(BaseModel):
    status: str
    llm_enabled: bool
    provider: str
    today_cost_usd: float
