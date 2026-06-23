"""Token-usage and cost tracking for LLM calls.

Each LLM call records its token counts and an estimated USD cost into the
`usage_records` table. Cost comes from the per-model price table in settings
($/1M tokens), so the figures are estimates that can be tuned without code
changes. The per-candidate and per-job cost totals shown in analytics are
derived from these rows.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import DEFAULT_TENANT_ID, UsageRecord

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
