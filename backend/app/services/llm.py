"""LLM service — Claude-backed JD extraction, cheap pre-filter, and deep scoring.

Patterns follow the claude-api skill:
- `client.messages.parse(..., output_format=PydanticModel)` for structured output.
- `claude-opus-4-8` for extraction + deep scoring; `claude-haiku-4-5` for the gate.
- The per-job criteria block is sent as a cached `system` block so a whole batch
  of CVs is billed for it once (verify via usage.cache_read_input_tokens).

The public surface is the `LLMService` protocol so the pipeline can be tested
with a fake implementation and no network calls.
"""
from __future__ import annotations

import json
from typing import Protocol

from app.config import get_settings
from app.schemas import (
    CandidateScoreLLM,
    PreFilterLLM,
    ScoringCriteriaLLM,
)

settings = get_settings()


class LLMUnavailableError(RuntimeError):
    """Raised when an LLM call is attempted without an API key configured."""


class LLMService(Protocol):
    def extract_criteria(self, jd_text: str) -> ScoringCriteriaLLM: ...

    def prefilter(self, criteria_summary: str, cv_text: str) -> PreFilterLLM: ...

    def deep_score(
        self, criteria_summary: str, cv_text: str
    ) -> CandidateScoreLLM: ...


def criteria_summary(
    required_skills: list[str],
    preferred_skills: list[str],
    min_years: int,
    must_haves: list[str],
    weights: dict | None = None,
) -> str:
    """Render criteria as a stable text block for caching + prompting."""
    return (
        "JOB SCORING CRITERIA\n"
        f"Required skills: {', '.join(required_skills) or '(none)'}\n"
        f"Preferred skills: {', '.join(preferred_skills) or '(none)'}\n"
        f"Minimum years of experience: {min_years}\n"
        f"Must-have qualifications: {', '.join(must_haves) or '(none)'}\n"
        f"Weights: {json.dumps(weights or {}, sort_keys=True)}\n"
    )


# --------------------------------------------------------------------------- #
# Real Claude implementation
# --------------------------------------------------------------------------- #
class AnthropicLLMService:
    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or settings.anthropic_api_key
        if not key:
            raise LLMUnavailableError("ANTHROPIC_API_KEY is not set.")
        import anthropic

        self._client = anthropic.Anthropic(api_key=key)

    def extract_criteria(self, jd_text: str) -> ScoringCriteriaLLM:
        resp = self._client.messages.parse(
            model=settings.model_deep,
            max_tokens=2000,
            system=(
                "You are an expert technical recruiter. Extract structured, "
                "screenable hiring criteria from a job description. Be specific "
                "and concrete; list individual skills, not sentences. Infer a "
                "reasonable minimum years of experience if implied."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Job description:\n\n{jd_text}",
                }
            ],
            output_format=ScoringCriteriaLLM,
        )
        return resp.parsed_output or ScoringCriteriaLLM()

    def prefilter(self, criteria_summary: str, cv_text: str) -> PreFilterLLM:
        resp = self._client.messages.parse(
            model=settings.model_cheap,
            max_tokens=300,
            system=[
                {
                    "type": "text",
                    "text": (
                        "You are a fast first-pass recruiting filter. Given the "
                        "job criteria and a CV, decide whether the candidate is "
                        "plausibly relevant enough to warrant a detailed review. "
                        "Be lenient — only filter out clearly unrelated CVs.\n\n"
                        + criteria_summary
                    ),
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {"role": "user", "content": f"CV:\n\n{cv_text[:6000]}"}
            ],
            output_format=PreFilterLLM,
        )
        return resp.parsed_output or PreFilterLLM(relevant=True, reason="parse fallback")

    def deep_score(self, criteria_summary: str, cv_text: str) -> CandidateScoreLLM:
        resp = self._client.messages.parse(
            model=settings.model_deep,
            max_tokens=2000,
            system=[
                {
                    "type": "text",
                    "text": (
                        "You are an expert technical recruiter scoring a CV "
                        "against a specific role. Score holistically but ground "
                        "your reasoning in the criteria. overall_score is 1-10 "
                        "(overall hire-worthiness for THIS role). job_match_pct "
                        "is 0-100 (how well the candidate's profile matches the "
                        "criteria). List concrete matched and missing skills. "
                        "Keep reasoning to 2-4 sentences, specific and fair.\n\n"
                        + criteria_summary
                    ),
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {"role": "user", "content": f"Candidate CV:\n\n{cv_text[:12000]}"}
            ],
            output_format=CandidateScoreLLM,
        )
        return resp.parsed_output or CandidateScoreLLM(
            overall_score=1, job_match_pct=0, reasoning="No structured output returned."
        )


def get_llm_service() -> LLMService:
    """Factory used by routers/pipeline. Raises if no key configured."""
    return AnthropicLLMService()
