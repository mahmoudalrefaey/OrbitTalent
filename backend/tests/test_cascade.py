"""Unit tests for the cost-optimized cascade (no network, no DB needed)."""
from app.models import ScoreStatus
from app.schemas import CandidateScoreLLM, QuickScoreLLM, ScoringCriteriaLLM
from app.services import cascade


class _Recorder:
    """Fake LLMService that records which tiers were invoked."""

    def __init__(self, *, quick: QuickScoreLLM, deep: CandidateScoreLLM | None = None,
                 embedding=None):
        self.calls: list[str] = []
        self._quick = quick
        self._deep = deep or CandidateScoreLLM(
            overall_score=9.0, job_match_pct=90.0, reasoning="deep"
        )
        self._embedding = embedding

    def extract_criteria(self, jd_text, db=None, tenant_id=1):
        return ScoringCriteriaLLM()

    def quick_score(self, criteria_summary, cv_text, db=None, tenant_id=1):
        self.calls.append("quick")
        return self._quick

    def deep_score(self, criteria_summary, cv_text, db=None, tenant_id=1):
        self.calls.append("deep")
        return self._deep

    def embed(self, text, db=None, tenant_id=1):
        self.calls.append("embed")
        return self._embedding


def _run(service, *, matched, required=("Python",), job_embedding=None):
    return cascade.run_cascade(
        service,
        criteria_summary="crit",
        required_skills=list(required),
        cv_text="some cv",
        matched_keywords=list(matched),
        missing_keywords=[],
        job_embedding=job_embedding,
        db=None,
    )


def test_tier0_filters_zero_coverage_without_any_llm_call():
    svc = _Recorder(quick=QuickScoreLLM(match_pct=99, confidence=1.0))
    res = _run(svc, matched=[])  # no required skill matched
    assert res.status == ScoreStatus.filtered_out
    assert res.tier_reached == 0
    assert svc.calls == []  # FREE — no LLM spend


def test_tier2_confident_skips_deep():
    svc = _Recorder(quick=QuickScoreLLM(match_pct=55, confidence=0.9))
    res = _run(svc, matched=["Python"])
    assert res.status == ScoreStatus.scored
    assert res.tier_reached == 2
    assert svc.calls == ["quick"]  # deep_score NOT called
    assert res.overall_score is not None


def test_strong_candidate_escalates_to_deep_even_if_confident():
    # High confidence but high match% -> escalate for a precise overall score.
    svc = _Recorder(quick=QuickScoreLLM(match_pct=85, confidence=0.95))
    res = _run(svc, matched=["Python"])
    assert res.tier_reached == 3
    assert svc.calls == ["quick", "deep"]
    assert res.overall_score == 9.0


def test_low_confidence_escalates_to_deep():
    svc = _Recorder(quick=QuickScoreLLM(match_pct=50, confidence=0.3))
    res = _run(svc, matched=["Python"])
    assert res.tier_reached == 3
    assert svc.calls == ["quick", "deep"]


def test_tier1_embedding_gate_filters_low_similarity():
    # Orthogonal vectors -> cosine 0 -> below threshold -> filtered at Tier 1.
    svc = _Recorder(
        quick=QuickScoreLLM(match_pct=99, confidence=1.0),
        embedding=[1.0, 0.0],
    )
    res = _run(svc, matched=["Python"], job_embedding=[0.0, 1.0])
    assert res.status == ScoreStatus.filtered_out
    assert res.tier_reached == 1
    assert svc.calls == ["embed"]  # quick/deep never reached
