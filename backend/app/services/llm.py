"""LLM service — OpenAI-compatible provider (g0i.ai /v1).

Provider:
- Uses the `openai` SDK pointed at `settings.llm_base_url` (g0i.ai's
  OpenAI-compatible endpoint). The API key ALWAYS comes from env.
- Structured output is obtained by asking the model for STRICT JSON matching a
  Pydantic schema, then parsing + validating (retry once on bad JSON). This
  works on any OpenAI-compatible chat model (e.g. qwen3-coder-80b), since not
  all of them support native JSON-mode / tool calling.
- Supports fallback models: if the primary model errors (plan/availability),
  each model in `settings.fallback_model_list` is tried in order.
- Every call records token usage + estimated cost (app.services.usage) when a
  DB session is provided, so cost tracking works for any provider.

Cascade surface (see app.services.cascade):
- `extract_criteria` — JD -> structured criteria (deep model).
- `quick_score`      — Tier 2: one cheap call, combined prefilter + score.
- `deep_score`       — Tier 3: deep model, precise overall score.
- `embed`            — optional Tier 1 embedding (only if model_embed set).

The public surface is the `LLMService` protocol so the pipeline can be tested
with a fake implementation and no network calls.
"""
from __future__ import annotations

import json
import logging
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import DEFAULT_TENANT_ID
from app.schemas import (
    CandidateScoreLLM,
    QuickScoreLLM,
    ScoringCriteriaLLM,
)
from app.services import usage as usage_svc

settings = get_settings()
logger = logging.getLogger("orbittalent.llm")

T = TypeVar("T", bound=BaseModel)


class LLMUnavailableError(RuntimeError):
    """Raised when an LLM call is attempted without an API key configured."""


class LLMService(Protocol):
    def extract_criteria(
        self, jd_text: str, db: Session | None = ..., tenant_id: int = ...
    ) -> ScoringCriteriaLLM: ...

    def quick_score(
        self, criteria_summary: str, cv_text: str,
        db: Session | None = ..., tenant_id: int = ...,
    ) -> QuickScoreLLM: ...

    def deep_score(
        self, criteria_summary: str, cv_text: str,
        db: Session | None = ..., tenant_id: int = ...,
    ) -> CandidateScoreLLM: ...

    def embed(
        self, text: str, db: Session | None = ..., tenant_id: int = ...
    ) -> list[float] | None: ...


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


def _schema_hint(model_cls: type[BaseModel]) -> str:
    """A compact description of the expected JSON, derived from the model."""
    fields = []
    for name, field in model_cls.model_fields.items():
        ann = field.annotation
        ann_name = getattr(ann, "__name__", str(ann))
        fields.append(f'  "{name}": <{ann_name}>')
    return "{\n" + ",\n".join(fields) + "\n}"


def _extract_json(text: str) -> str:
    """Pull a JSON object out of a model response (strips code fences/prose)."""
    t = text.strip()
    if t.startswith("```"):
        # ```json ... ``` or ``` ... ```
        t = t.split("```", 2)[1] if t.count("```") >= 2 else t.strip("`")
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    # Fall back to the outermost { ... } span.
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1 and end > start:
        return t[start : end + 1]
    return t.strip()


# --------------------------------------------------------------------------- #
# OpenAI-compatible implementation (g0i.ai /v1)
# --------------------------------------------------------------------------- #
class ProviderLLMService:
    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or settings.api_key
        if not key:
            raise LLMUnavailableError(
                "LLM_API_KEY is not set. Set it in the environment to enable scoring."
            )
        from openai import OpenAI

        self._client = OpenAI(base_url=settings.llm_base_url, api_key=key)

    # -- internal helpers ---------------------------------------------------
    def _models_to_try(self, primary: str) -> list[str]:
        seen: dict[str, None] = {}
        for m in (primary, *settings.fallback_model_list):
            if m and m not in seen:
                seen[m] = None
        return list(seen)

    def _structured(
        self,
        *,
        primary_model: str,
        tier: int,
        db: Session | None,
        system: str,
        user: str,
        schema: type[T],
        max_tokens: int,
        tenant_id: int = DEFAULT_TENANT_ID,
    ) -> T | None:
        """Chat-completion that returns a validated Pydantic object.

        Asks for strict JSON; parses + validates; retries once with a stricter
        nudge on bad JSON. Tries fallback models on API errors. Returns None if
        everything fails (callers supply a safe default).
        """
        instruction = (
            f"{system}\n\n"
            "Respond with ONLY a single JSON object — no markdown, no code "
            "fences, no commentary. It must match this shape:\n"
            f"{_schema_hint(schema)}"
        )
        last_exc: Exception | None = None

        for model in self._models_to_try(primary_model):
            messages = [
                {"role": "system", "content": instruction},
                {"role": "user", "content": user},
            ]
            for attempt in range(2):  # one retry on unparseable output
                try:
                    resp = self._client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=0,
                    )
                except Exception as exc:  # noqa: BLE001 — try next model
                    last_exc = exc
                    logger.warning("LLM call on model %s failed: %s", model, exc)
                    break  # move to next model, don't burn the retry here

                if db is not None and getattr(resp, "usage", None) is not None:
                    usage_svc.record_usage(
                        db,
                        model=model,
                        tier=tier,
                        usage=usage_svc.TokenUsage.from_response(resp.usage),
                        tenant_id=tenant_id,
                    )

                raw = resp.choices[0].message.content or ""
                try:
                    return schema.model_validate_json(_extract_json(raw))
                except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                    last_exc = exc
                    logger.warning(
                        "Bad JSON from %s (attempt %d): %s", model, attempt + 1, exc
                    )
                    messages.append({"role": "assistant", "content": raw[:500]})
                    messages.append(
                        {
                            "role": "user",
                            "content": "That was not valid JSON for the schema. "
                            "Reply with ONLY the corrected JSON object.",
                        }
                    )

        if last_exc:
            logger.error("All models exhausted for tier %s: %s", tier, last_exc)
        return None

    # -- public surface -----------------------------------------------------
    def extract_criteria(
        self,
        jd_text: str,
        db: Session | None = None,
        tenant_id: int = DEFAULT_TENANT_ID,
    ) -> ScoringCriteriaLLM:
        out = self._structured(
            primary_model=settings.model_deep,
            tier=-1,
            db=db,
            tenant_id=tenant_id,
            system=(
                "You are an expert technical recruiter. Extract structured, "
                "screenable hiring criteria from a job description. Be specific "
                "and concrete; list individual skills, not sentences. Infer a "
                "reasonable minimum years of experience if implied."
            ),
            user=f"Job description:\n\n{jd_text}",
            schema=ScoringCriteriaLLM,
            max_tokens=2000,
        )
        return out or ScoringCriteriaLLM()

    def quick_score(
        self,
        criteria_summary: str,
        cv_text: str,
        db: Session | None = None,
        tenant_id: int = DEFAULT_TENANT_ID,
    ) -> QuickScoreLLM:
        """Tier 2 — ONE cheap call that both screens and scores."""
        out = self._structured(
            primary_model=settings.model_cheap,
            tier=2,
            db=db,
            tenant_id=tenant_id,
            system=(
                "You are a fast, cost-efficient recruiting screener. Given the "
                "job criteria and a CV, output a job match percentage (0-100), "
                "your confidence (0-1) in that score, the top gaps, and a "
                "one-sentence summary. Be decisive: only use low confidence "
                "when the CV is genuinely ambiguous for this role.\n\n"
                + criteria_summary
            ),
            user=f"CV:\n\n{cv_text[:8000]}",
            schema=QuickScoreLLM,
            max_tokens=400,
        )
        return out or QuickScoreLLM(
            match_pct=0, confidence=0.0, summary="No structured output returned."
        )

    def deep_score(
        self,
        criteria_summary: str,
        cv_text: str,
        db: Session | None = None,
        tenant_id: int = DEFAULT_TENANT_ID,
    ) -> CandidateScoreLLM:
        out = self._structured(
            primary_model=settings.model_deep,
            tier=3,
            db=db,
            tenant_id=tenant_id,
            system=(
                "You are an expert technical recruiter scoring a CV against a "
                "specific role. Score holistically but ground your reasoning in "
                "the criteria. overall_score is 1-10 (overall hire-worthiness "
                "for THIS role). job_match_pct is 0-100 (how well the "
                "candidate's profile matches the criteria). List concrete "
                "matched and missing skills. Keep reasoning to 2-4 sentences, "
                "specific and fair.\n\n" + criteria_summary
            ),
            user=f"Candidate CV:\n\n{cv_text[:12000]}",
            schema=CandidateScoreLLM,
            max_tokens=2000,
        )
        return out or CandidateScoreLLM(
            overall_score=1, job_match_pct=0, reasoning="No structured output returned."
        )

    def embed(
        self,
        text: str,
        db: Session | None = None,
        tenant_id: int = DEFAULT_TENANT_ID,
    ) -> list[float] | None:
        """Optional Tier-1 embedding. Returns None if disabled or unsupported."""
        if not settings.model_embed:
            return None
        try:
            resp = self._client.embeddings.create(
                model=settings.model_embed, input=text[:8000]
            )
            if db is not None and getattr(resp, "usage", None) is not None:
                usage_svc.record_usage(
                    db,
                    model=settings.model_embed,
                    tier=1,
                    usage=usage_svc.TokenUsage.from_response(resp.usage),
                    tenant_id=tenant_id,
                )
            return list(resp.data[0].embedding)
        except Exception as exc:  # noqa: BLE001 — embeddings are best-effort
            logger.info("Embeddings unavailable (%s); skipping Tier 1.", exc)
            return None


def get_llm_service() -> LLMService:
    """Factory used by routers/pipeline. Raises if no key configured."""
    return ProviderLLMService()
