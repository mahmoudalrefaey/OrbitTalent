"""Unit tests for the cost-optimized cascade (no network, no DB needed)."""
from app.models import ScoreStatus
from app.schemas import CandidateScoreLLM, QuickScoreLLM, ScoringCriteriaLLM
from app.services import cascade


class _Recorder:
    """Fake LLMService that records which tiers were invoked."""

    def __init__(self, *, quick: QuickScoreLLM, deep: CandidateScoreLLM | None = None):
        self.calls: list[str] = []
        self._quick = quick
        self._deep = deep or CandidateScoreLLM(
            overall_score=9.0, job_match_pct=90.0, reasoning="deep"
        )

    def extract_criteria(self, jd_text, db=None, tenant_id=1):
        return ScoringCriteriaLLM()

    def quick_score(self, criteria_summary, cv_text, db=None, tenant_id=1):
        self.calls.append("quick")
        return self._quick

    def deep_score(self, criteria_summary, cv_text, db=None, tenant_id=1):
        self.calls.append("deep")
        return self._deep


def _run(service, *, matched, required=("Python",), jd_text="", cv_text="some cv",
         preferred=()):
    return cascade.run_cascade(
        service,
        criteria_summary="crit",
        required_skills=list(required),
        preferred_skills=list(preferred),
        jd_text=jd_text,
        cv_text=cv_text,
        matched_keywords=list(matched),
        missing_keywords=[],
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


def test_tier1_similarity_gate_filters_unrelated_cv(monkeypatch):
    # Pin the Tier-1 threshold for this test (independent of .env/conftest).
    monkeypatch.setattr(cascade.settings, "tier1_min_similarity", 0.35)
    # CV text shares the required skill keyword (passes Tier 0) but is otherwise
    # unrelated to the JD → low BM25+skill similarity → filtered at Tier 1,
    # with NO LLM calls.
    svc = _Recorder(quick=QuickScoreLLM(match_pct=99, confidence=1.0))
    res = _run(
        svc,
        matched=["Python"],
        required=("Python", "FastAPI", "PostgreSQL", "AWS", "Kubernetes"),
        jd_text=(
            "Senior backend engineer. Must have deep FastAPI, PostgreSQL, AWS, "
            "Kubernetes, distributed systems, microservices experience. "
        ) * 3,
        cv_text="Python hobbyist. Mostly wrote small scripts. No web frameworks.",
    )
    assert res.status == ScoreStatus.filtered_out
    assert res.tier_reached == 1
    assert svc.calls == []  # deterministic — zero LLM spend


def test_tier1_passes_relevant_cv_through_to_llm(monkeypatch):
    monkeypatch.setattr(cascade.settings, "tier1_min_similarity", 0.35)
    # A CV that closely matches the JD clears Tier 1 and proceeds to the LLM.
    svc = _Recorder(quick=QuickScoreLLM(match_pct=80, confidence=0.95))
    res = _run(
        svc,
        matched=["Python", "FastAPI"],
        required=("Python", "FastAPI"),
        jd_text="Backend engineer with Python and FastAPI building REST APIs.",
        cv_text=(
            "Senior backend engineer. 7 years Python and FastAPI building REST "
            "APIs, microservices, PostgreSQL. Strong system design."
        ),
    )
    assert res.tier_reached >= 2  # cleared Tier 1
    assert "quick" in svc.calls
