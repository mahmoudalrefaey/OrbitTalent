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
    new = "new"
    shortlisted = "shortlisted"
    interview = "interview"
    rejected = "rejected"


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
    # 1=embedding gate, 2=cheap LLM, 3=deep LLM). Backs analytics cost metrics.
    tier_reached: Mapped[int] = mapped_column(Integer, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    est_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    stage: Mapped[CandidateStage] = mapped_column(
        Enum(CandidateStage), default=CandidateStage.new
    )
    score_status: Mapped[ScoreStatus] = mapped_column(
        Enum(ScoreStatus), default=ScoreStatus.pending
    )
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    job: Mapped[Job] = relationship(back_populates="candidates")


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
