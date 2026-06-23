"""SQLAlchemy ORM models. Tenant-scoped from day one (MVP uses one default tenant)."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

DEFAULT_TENANT_ID = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, enum.Enum):
    draft = "draft"          # created, JD pasted, criteria not yet confirmed
    ready = "ready"          # criteria confirmed, accepting CVs
    archived = "archived"


class CandidateStage(str, enum.Enum):
    # Full ATS lifecycle (V2). Order matters for funnel/conversion analytics.
    new = "new"
    ai_screened = "ai_screened"
    qualified = "qualified"
    shortlisted = "shortlisted"
    assessment_pending = "assessment_pending"
    assessment_passed = "assessment_passed"
    interview_scheduled = "interview_scheduled"
    interview_passed = "interview_passed"
    final_review = "final_review"
    offer_sent = "offer_sent"
    hired = "hired"
    rejected = "rejected"
    withdrawn = "withdrawn"


# Ordered funnel of the "happy path" stages (excludes terminal rejected/withdrawn)
# — used by analytics for funnel counts + stage→stage conversion rates.
STAGE_FUNNEL_ORDER: list[CandidateStage] = [
    CandidateStage.new,
    CandidateStage.ai_screened,
    CandidateStage.qualified,
    CandidateStage.shortlisted,
    CandidateStage.assessment_pending,
    CandidateStage.assessment_passed,
    CandidateStage.interview_scheduled,
    CandidateStage.interview_passed,
    CandidateStage.final_review,
    CandidateStage.offer_sent,
    CandidateStage.hired,
]


class RejectionReason(str, enum.Enum):
    low_ai_score = "low_ai_score"
    missing_required_skills = "missing_required_skills"
    wrong_experience_level = "wrong_experience_level"
    wrong_location = "wrong_location"
    country_restriction = "country_restriction"
    duplicate_application = "duplicate_application"
    recruiter_decision = "recruiter_decision"


class ScoreStatus(str, enum.Enum):
    pending = "pending"      # uploaded, not yet processed
    processing = "processing"
    scored = "scored"
    failed = "failed"
    filtered_out = "filtered_out"   # rejected by cheap pre-filter, no deep score


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    jobs: Mapped[list[Job]] = relationship(back_populates="tenant")
    # 1:1 — each user owns exactly one tenant (data-isolation model).
    user: Mapped[User | None] = relationship(
        back_populates="tenant", uselist=False
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # One tenant per user; unique enforces the 1:1 isolation boundary.
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), unique=True, index=True
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    tenant: Mapped[Tenant] = relationship(back_populates="user")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), default=DEFAULT_TENANT_ID, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    jd_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.draft
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    tenant: Mapped[Tenant] = relationship(back_populates="jobs")
    criteria: Mapped[ScoringCriteria | None] = relationship(
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    candidates: Mapped[list[Candidate]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class ScoringCriteria(Base):
    __tablename__ = "scoring_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"), unique=True, index=True
    )
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    min_years: Mapped[int] = mapped_column(Integer, default=0)
    must_haves: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Relative importance, e.g. {"required_skills": 0.5, "preferred_skills": 0.2, ...}
    weights: Mapped[dict] = mapped_column(JSON, default=dict)

    # --- Hiring rules (V2) — feed scoring + automation. All optional. ---
    geo_allow: Mapped[list[str]] = mapped_column(JSON, default=list)   # allowed countries
    geo_block: Mapped[list[str]] = mapped_column(JSON, default=list)   # auto-reject countries
    min_degree: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_universities: Mapped[list[str]] = mapped_column(JSON, default=list)
    min_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # AI ranking importance, e.g. {"skills": 0.4, "experience": 0.2, "education": 0.15, ...}
    ranking_weights: Mapped[dict] = mapped_column(JSON, default=dict)

    job: Mapped[Job] = relationship(back_populates="criteria")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"), index=True
    )
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), default=DEFAULT_TENANT_ID, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    parsed_text: Mapped[str] = mapped_column(Text, default="")

    # Two distinct scores + overall.
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)        # 0-100
    job_match_pct: Mapped[float | None] = mapped_column(Float, nullable=True)    # 0-100
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)    # 1-10

    ats_issues: Mapped[list[str]] = mapped_column(JSON, default=list)
    matched_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    missing_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    reasoning: Mapped[str] = mapped_column(Text, default="")

    # Cascade efficiency telemetry.
    # tier_reached: highest cascade tier this CV consumed (0=deterministic,
    # 1=similarity gate, 2=cheap LLM, 3=deep LLM). Backs analytics cost metrics.
    tier_reached: Mapped[int] = mapped_column(Integer, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    est_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # --- ATS profile fields (V2) — LLM-extracted at scoring time or edited. ---
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    education: Mapped[str | None] = mapped_column(String(255), nullable=True)
    certifications: Mapped[list[str]] = mapped_column(JSON, default=list)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    expected_salary: Mapped[int | None] = mapped_column(Integer, nullable=True)

    stage: Mapped[CandidateStage] = mapped_column(
        Enum(CandidateStage), default=CandidateStage.new
    )
    # Set only when stage == rejected.
    rejection_reason: Mapped[RejectionReason | None] = mapped_column(
        Enum(RejectionReason), nullable=True
    )
    # Recruiter this candidate is assigned to (FK users, null = unassigned).
    assigned_recruiter_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    score_status: Mapped[ScoreStatus] = mapped_column(
        Enum(ScoreStatus), default=ScoreStatus.pending
    )
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    # Distinct from created_at so imported/backdated applications keep their date.
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    job: Mapped[Job] = relationship(back_populates="candidates")
    stage_events: Mapped[list[StageEvent]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="StageEvent.at",
    )


class StageEvent(Base):
    """Append-only history of candidate stage transitions.

    Powers funnel counts, stage→stage conversion rates, time-in-stage, and
    recruiter response-time metrics. Written on every stage change (manual,
    bulk, or automation). `from_stage` is null for the initial 'new' event.
    """

    __tablename__ = "stage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), index=True
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id"), index=True
    )
    from_stage: Mapped[CandidateStage | None] = mapped_column(
        Enum(CandidateStage), nullable=True
    )
    to_stage: Mapped[CandidateStage] = mapped_column(Enum(CandidateStage))
    reason: Mapped[str] = mapped_column(Text, default="")
    # Null = system/automation; else the user who made the change.
    by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)

    candidate: Mapped[Candidate] = relationship(back_populates="stage_events")


class AutomationRule(Base):
    """Recruiter-configured auto-reject / auto-progress / auto-assign rule.

    Conditions + action are stored as JSON so the rule vocabulary can grow
    without migrations. Evaluated by app.services.automation.
    """

    __tablename__ = "automation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), index=True
    )
    # Null = applies to all jobs in the tenant; else scoped to one job.
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), default="")
    # e.g. [{"field": "overall_score", "op": "lt", "value": 6}, ...]
    trigger_json: Mapped[list] = mapped_column(JSON, default=list)
    # e.g. {"type": "reject", "reason": "low_ai_score"} or {"type": "move", "stage": "shortlisted"}
    action_json: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class UsageRecord(Base):
    """One row per LLM call — token counts + estimated cost for tracking."""

    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), default=DEFAULT_TENANT_ID, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, index=True
    )
    model: Mapped[str] = mapped_column(String(128), default="")
    # Cascade tier that issued the call (0-3); -1 for non-cascade calls
    # like JD criteria extraction.
    tier: Mapped[int] = mapped_column(Integer, default=-1)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
