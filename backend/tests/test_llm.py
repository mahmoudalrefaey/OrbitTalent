"""Tests for the LLM service layer that don't hit the network.

The real AnthropicLLMService is exercised only by the optional smoke test
(test_llm_smoke.py, skipped without ANTHROPIC_API_KEY). Here we verify the
prompt-building helper and that a fake conforming to the LLMService protocol
works as the pipeline expects.
"""
from app.schemas import CandidateScoreLLM, QuickScoreLLM, ScoringCriteriaLLM
from app.services import llm


def test_criteria_summary_is_stable_and_complete():
    s = llm.criteria_summary(
        required_skills=["Python", "FastAPI"],
        preferred_skills=["React"],
        min_years=3,
        must_haves=["Bachelor's degree"],
        weights={"required_skills": 0.6},
    )
    assert "Python, FastAPI" in s
    assert "Minimum years of experience: 3" in s
    assert "Bachelor's degree" in s
    # Stable across calls (important for prompt caching).
    again = llm.criteria_summary(["Python", "FastAPI"], ["React"], 3, ["Bachelor's degree"], {"required_skills": 0.6})
    assert s == again


def test_criteria_summary_handles_empty():
    s = llm.criteria_summary([], [], 0, [])
    assert "(none)" in s


class FakeLLM:
    """Conforms to the (cascade) LLMService protocol for pipeline tests."""

    def extract_criteria(self, jd_text: str, db=None, tenant_id=1) -> ScoringCriteriaLLM:
        return ScoringCriteriaLLM(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["React"],
            min_years=3,
            must_haves=["Bachelor's degree"],
        )

    def quick_score(self, criteria_summary: str, cv_text: str, db=None, tenant_id=1) -> QuickScoreLLM:
        relevant = "python" in cv_text.lower()
        return QuickScoreLLM(
            match_pct=60.0 if relevant else 5.0,
            confidence=0.9 if relevant else 0.95,
            top_gaps=["React"],
            summary="keyword check",
        )

    def deep_score(self, criteria_summary: str, cv_text: str, db=None, tenant_id=1) -> CandidateScoreLLM:
        return CandidateScoreLLM(
            overall_score=8.0,
            job_match_pct=82.0,
            matched_keywords=["Python"],
            missing_keywords=["React"],
            reasoning="Strong backend match.",
        )


def test_fake_llm_satisfies_protocol():
    fake: llm.LLMService = FakeLLM()
    crit = fake.extract_criteria("some JD")
    assert crit.required_skills == ["Python", "FastAPI"]
    q_yes = fake.quick_score("c", "I know Python")
    q_no = fake.quick_score("c", "I cook food")
    assert q_yes.match_pct > q_no.match_pct
    assert 0 <= q_yes.confidence <= 1
    score = fake.deep_score("c", "Python dev")
    assert 1 <= score.overall_score <= 10
    assert 0 <= score.job_match_pct <= 100
