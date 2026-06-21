"""Usage tracking & cost estimation for LLM calls.

Every LLM call (regardless of provider) records token counts and an estimated
USD cost into the `usage_records` table. Cost is computed from the per-model
price table in settings ($/1M tokens), so it works for any Anthropic-compatible
gateway — the numbers are estimates, tunable via env without code changes.

The aggregation helpers produce the exact shapes declared in `schemas.py`
(`UsageOut`, `UsagePerDay`) for the `GET /usage` endpoint and the analytics
cascade-cost fields.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import DEFAULT_TENANT_ID, UsageRecord
from app.schemas import UsageOut, UsagePerDay

settings = get_settings()

_PER_MILLION = 1_000_000.0


@dataclass
class TokenUsage:
    """Normalized token counts pulled from a provider response.

    Anthropic-style usage exposes input_tokens / output_tokens and
    cache_read_input_tokens / cache_creation_input_tokens. We treat cache reads
    as `cached` (billed at the discounted rate) and everything else as input.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0

    @classmethod
    def from_response(cls, usage) -> "TokenUsage":
        """Best-effort extraction from a provider usage object.

        Handles the OpenAI shape (prompt_tokens / completion_tokens, with
        cached tokens nested under prompt_tokens_details) and falls back to the
        Anthropic shape (input_tokens / output_tokens). Tolerant of missing
        fields so an unfamiliar gateway never crashes the pipeline.
        """
        def g(obj, name: str) -> int:
            return int(getattr(obj, name, 0) or 0)

        # OpenAI-style cached tokens live under prompt_tokens_details.cached_tokens.
        details = getattr(usage, "prompt_tokens_details", None)
        cached = g(details, "cached_tokens") if details is not None else 0
        if not cached:
            cached = g(usage, "cache_read_input_tokens")  # Anthropic fallback

        prompt = g(usage, "prompt_tokens") or (
            g(usage, "input_tokens") + g(usage, "cache_creation_input_tokens")
        )
        completion = g(usage, "completion_tokens") or g(usage, "output_tokens")

        # OpenAI's prompt_tokens already includes cached; keep them separate for
        # pricing without double-counting.
        return cls(
            prompt_tokens=max(0, prompt - cached),
            completion_tokens=completion,
            cached_tokens=cached,
        )


def estimate_cost(model: str, usage: TokenUsage) -> float:
    """USD cost estimate for one call from the settings price table."""
    price = settings.price_for(model)
    cost = (
        usage.prompt_tokens * price["input"]
        + usage.completion_tokens * price["output"]
        + usage.cached_tokens * price["cached"]
    ) / _PER_MILLION
    return round(cost, 6)


def record_usage(
    db: Session,
    *,
    model: str,
    tier: int,
    usage: TokenUsage,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> float:
    """Persist one usage row and return its estimated cost.

    Commits its own row so a failure to score a candidate later does not roll
    back the usage accounting.
    """
    cost = estimate_cost(model, usage)
    db.add(
        UsageRecord(
            tenant_id=tenant_id,
            model=model,
            tier=tier,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cached_tokens=usage.cached_tokens,
            cost_usd=cost,
        )
    )
    db.commit()
    return cost


# --------------------------------------------------------------------------- #
# Aggregation for GET /usage and analytics
# --------------------------------------------------------------------------- #
def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def today_cost(db: Session, tenant_id: int = DEFAULT_TENANT_ID) -> float:
    today = _today_utc()
    rows = db.scalars(
        select(UsageRecord).where(UsageRecord.tenant_id == tenant_id)
    ).all()
    return round(
        sum(r.cost_usd for r in rows if r.created_at.strftime("%Y-%m-%d") == today),
        4,
    )


def build_usage_out(db: Session, tenant_id: int = DEFAULT_TENANT_ID) -> UsageOut:
    """Aggregate all usage rows into the API's UsageOut shape."""
    rows = db.scalars(
        select(UsageRecord).where(UsageRecord.tenant_id == tenant_id)
    ).all()

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    week_ago = now - timedelta(days=7)

    by_day: dict[str, UsagePerDay] = {}
    by_tier: dict[str, int] = defaultdict(int)
    by_model: dict[str, int] = defaultdict(int)
    today_total = 0.0
    week_total = 0.0
    cached_sum = 0
    prompt_sum = 0

    for r in rows:
        day = r.created_at.strftime("%Y-%m-%d")
        bucket = by_day.get(day)
        if bucket is None:
            bucket = UsagePerDay(
                date=day,
                cost_usd=0.0,
                calls=0,
                cached_tokens=0,
                prompt_tokens=0,
                completion_tokens=0,
            )
            by_day[day] = bucket
        bucket.cost_usd = round(bucket.cost_usd + r.cost_usd, 6)
        bucket.calls += 1
        bucket.cached_tokens += r.cached_tokens
        bucket.prompt_tokens += r.prompt_tokens
        bucket.completion_tokens += r.completion_tokens

        by_tier[f"tier_{r.tier}"] += 1
        by_model[r.model or "unknown"] += 1

        if day == today:
            today_total += r.cost_usd
        if r.created_at >= week_ago:
            week_total += r.cost_usd
        cached_sum += r.cached_tokens
        prompt_sum += r.prompt_tokens

    total_input = cached_sum + prompt_sum
    cache_hit_rate = round(cached_sum / total_input, 4) if total_input else 0.0

    return UsageOut(
        provider=settings.provider,
        today_cost_usd=round(today_total, 4),
        last_7_days_cost_usd=round(week_total, 4),
        total_calls=len(rows),
        cache_hit_rate=cache_hit_rate,
        by_day=sorted(by_day.values(), key=lambda d: d.date),
        by_tier=dict(by_tier),
        by_model=dict(by_model),
    )
