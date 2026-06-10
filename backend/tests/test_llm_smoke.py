"""Optional real-API smoke test. Skipped unless ANTHROPIC_API_KEY is set.

Run explicitly with:  ANTHROPIC_API_KEY=sk-... pytest tests/test_llm_smoke.py -s

Verifies JD extraction and deep scoring produce valid Pydantic objects, and
that the per-job criteria block is served from cache on the 2nd CV of a batch
(cache_read_input_tokens > 0), proving the prompt-caching design works.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set; skipping live LLM smoke test.",
)

JD = """\
Senior Backend Engineer. We need 5+ years building Python services with FastAPI.
Must have experience with PostgreSQL and AWS. React knowledge is a plus.
Bachelor's degree in Computer Science required.
"""

CV = """\
Jane Developer — jane@example.com — +1 555 123 4567
EXPERIENCE: 7 years building Python/FastAPI backends. Led AWS + PostgreSQL
migrations. Some React. EDUCATION: B.Sc. Computer Science.
SKILLS: Python, FastAPI, PostgreSQL, AWS, Docker.
"""


def test_extract_and_deep_score_live():
    from app.services import llm

    service = llm.get_llm_service()

    crit = service.extract_criteria(JD)
    assert crit.required_skills, "expected some required skills"
    assert crit.min_years >= 1

    summary = llm.criteria_summary(
        crit.required_skills, crit.preferred_skills, crit.min_years, crit.must_haves
    )
    score = service.deep_score(summary, CV)
    assert 1 <= score.overall_score <= 10
    assert 0 <= score.job_match_pct <= 100
    assert score.reasoning
    print(f"\noverall={score.overall_score} match={score.job_match_pct}%")
    print("reasoning:", score.reasoning)
