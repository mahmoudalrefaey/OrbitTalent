"""API integration tests using FastAPI TestClient against a temp SQLite DB.

LLM calls are stubbed by monkeypatching llm.get_llm_service so no network or
API key is needed. Background tasks run synchronously under TestClient.
"""
import io

import pytest
from fastapi.testclient import TestClient


def register_user(client: TestClient, email="user@example.com", password="password123", name="Test"):
    """Register a user; the TestClient stores the returned session cookie."""
    r = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def client():
    """Authenticated app client against the temp DB configured in conftest.

    Each test gets a clean schema, then registers + logs in a default user so
    the session cookie is present on the client for all app endpoints. LLM is
    patched per-test via _use_fake_llm.
    """
    import app.services.llm as llm_mod
    from app.db import Base, engine, init_db
    from app.main import app

    Base.metadata.drop_all(bind=engine)
    init_db()  # create_all + seed default tenant

    # Reset any prior fake-LLM patch (real factory raises without a key).
    llm_mod.get_llm_service = _real_get_llm_service

    with TestClient(app) as c:
        c._llm_mod = llm_mod
        register_user(c)  # sets ot_session cookie on the client
        yield c


# Capture the genuine factory once so we can restore it between tests.
import app.services.llm as _llm_for_capture  # noqa: E402

_real_get_llm_service = _llm_for_capture.get_llm_service


class FakeLLM:
    """Conforms to the new (cascade) LLMService protocol.

    quick_score returns LOW confidence so the cascade escalates to deep_score,
    letting the existing end-to-end assertions (overall=8.0) hold. embed is
    disabled (returns None) so Tier 1 is skipped.
    """

    def extract_criteria(self, jd_text, db=None, tenant_id=1):
        from app.schemas import ScoringCriteriaLLM
        return ScoringCriteriaLLM(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["React"],
            min_years=3,
            must_haves=["Bachelor's degree"],
        )

    def quick_score(self, criteria_summary, cv_text, db=None, tenant_id=1):
        from app.schemas import QuickScoreLLM
        relevant = "python" in cv_text.lower()
        return QuickScoreLLM(
            # 0 match for irrelevant CVs (no required skill) -> Tier 0 filter;
            # otherwise low confidence -> escalate to deep_score.
            match_pct=60.0 if relevant else 0.0,
            confidence=0.4 if relevant else 0.9,
            top_gaps=["React"],
            summary="kw",
        )

    def deep_score(self, criteria_summary, cv_text, db=None, tenant_id=1):
        from app.schemas import CandidateScoreLLM
        return CandidateScoreLLM(
            overall_score=8.0, job_match_pct=82.0,
            matched_keywords=["Python"], missing_keywords=["React"],
            reasoning="Strong backend match.",
        )

    def embed(self, text, db=None, tenant_id=1):
        return None


def _use_fake_llm(client):
    fake = FakeLLM()
    client._llm_mod.get_llm_service = lambda: fake
    # The candidates background task and jobs router both call get_llm_service
    # via the llm module reference, so patching the module attr covers both.


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_list_job(client):
    r = client.post("/jobs", json={"title": "Backend Engineer", "jd_text": "Python role"})
    assert r.status_code == 201
    job = r.json()
    assert job["title"] == "Backend Engineer"
    assert job["candidate_count"] == 0

    r2 = client.get("/jobs")
    assert r2.status_code == 200
    assert len(r2.json()) == 1


def test_extract_criteria_requires_llm(client):
    # No API key configured -> 503.
    r = client.post("/jobs", json={"title": "X", "jd_text": "Need Python."})
    job_id = r.json()["id"]
    r2 = client.post(f"/jobs/{job_id}/extract-criteria", json={})
    assert r2.status_code == 503


def test_extract_criteria_with_fake_llm(client):
    _use_fake_llm(client)
    r = client.post("/jobs", json={"title": "X", "jd_text": "Need Python and FastAPI."})
    job_id = r.json()["id"]
    r2 = client.post(f"/jobs/{job_id}/extract-criteria", json={})
    assert r2.status_code == 200
    crit = r2.json()
    assert "Python" in crit["required_skills"]
    assert crit["min_years"] == 3


def test_update_criteria_sets_ready(client):
    r = client.post("/jobs", json={"title": "X", "jd_text": "Need Python."})
    job_id = r.json()["id"]
    r2 = client.put(
        f"/jobs/{job_id}/criteria",
        json={
            "required_skills": ["Python"],
            "preferred_skills": [],
            "min_years": 2,
            "must_haves": [],
            "weights": {},
        },
    )
    assert r2.status_code == 200
    detail = client.get(f"/jobs/{job_id}").json()
    assert detail["status"] == "ready"
    assert detail["criteria"]["required_skills"] == ["Python"]


def test_upload_and_score_candidate_end_to_end(client):
    _use_fake_llm(client)
    # Create job + criteria.
    job_id = client.post("/jobs", json={"title": "Backend", "jd_text": "Python"}).json()["id"]
    client.put(
        f"/jobs/{job_id}/criteria",
        json={
            "required_skills": ["Python", "FastAPI"],
            "preferred_skills": ["React"],
            "min_years": 3,
            "must_haves": [],
            "weights": {},
        },
    )

    cv = (
        "Jane Developer\njane@example.com | +1 555 123 4567\n"
        "EXPERIENCE\nBuilt services in Python and FastAPI for five years. "
        "Worked with React and PostgreSQL. " * 5
        + "\nEDUCATION\nB.Sc. Computer Science\nSKILLS\nPython, FastAPI, React"
    ).encode()

    r = client.post(
        f"/jobs/{job_id}/candidates",
        files=[("files", ("jane.txt", io.BytesIO(cv), "text/plain"))],
    )
    assert r.status_code == 202
    cand_id = r.json()[0]["id"]

    # Background task ran synchronously under TestClient — fetch the result.
    detail = client.get(f"/candidates/{cand_id}").json()
    assert detail["score_status"] == "scored"
    assert detail["ats_score"] is not None and detail["ats_score"] > 50
    assert detail["overall_score"] == 8.0
    assert detail["job_match_pct"] == 82.0
    assert "Python" in detail["matched_keywords"]


def test_filtered_out_candidate(client):
    _use_fake_llm(client)
    job_id = client.post("/jobs", json={"title": "Backend", "jd_text": "Python"}).json()["id"]
    client.put(
        f"/jobs/{job_id}/criteria",
        json={"required_skills": ["Python"], "preferred_skills": [], "min_years": 1, "must_haves": [], "weights": {}},
    )
    # CV with no 'python' -> fake prefilter marks irrelevant.
    cv = (
        "Bob Baker\nbob@example.com | +1 555 999 8888\n"
        "EXPERIENCE\nPastry chef for ten years making bread and cakes. " * 6
        + "\nEDUCATION\nCulinary school\nSKILLS\nBaking, cooking"
    ).encode()
    r = client.post(
        f"/jobs/{job_id}/candidates",
        files=[("files", ("bob.txt", io.BytesIO(cv), "text/plain"))],
    )
    cand_id = r.json()[0]["id"]
    detail = client.get(f"/candidates/{cand_id}").json()
    assert detail["score_status"] == "filtered_out"
    # ATS still scored even though filtered out of deep scoring.
    assert detail["ats_score"] is not None


def test_stage_update(client):
    _use_fake_llm(client)
    job_id = client.post("/jobs", json={"title": "B", "jd_text": "Python"}).json()["id"]
    client.put(
        f"/jobs/{job_id}/criteria",
        json={"required_skills": ["Python"], "preferred_skills": [], "min_years": 1, "must_haves": [], "weights": {}},
    )
    cv = ("a@b.com +1 555 111 2222 EXPERIENCE Python developer. " * 20).encode()
    cand_id = client.post(
        f"/jobs/{job_id}/candidates",
        files=[("files", ("c.txt", io.BytesIO(cv), "text/plain"))],
    ).json()[0]["id"]

    r = client.patch(f"/candidates/{cand_id}/stage", json={"stage": "shortlisted"})
    assert r.status_code == 200
    assert r.json()["stage"] == "shortlisted"


def test_analytics(client):
    _use_fake_llm(client)
    job_id = client.post("/jobs", json={"title": "B", "jd_text": "Python"}).json()["id"]
    client.put(
        f"/jobs/{job_id}/criteria",
        json={"required_skills": ["Python", "React"], "preferred_skills": [], "min_years": 1, "must_haves": [], "weights": {}},
    )
    cv = ("a@b.com +1 555 111 2222 EXPERIENCE Python developer. " * 20).encode()
    client.post(
        f"/jobs/{job_id}/candidates",
        files=[("files", ("c.txt", io.BytesIO(cv), "text/plain"))],
    )
    r = client.get(f"/jobs/{job_id}/analytics")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["scored"] == 1
    assert "stage_counts" in data
    # Cascade telemetry present.
    assert "tier_distribution" in data
    assert sum(data["tier_distribution"].values()) == 1
    assert "est_total_cost_usd" in data


def test_usage_endpoint(client):
    r = client.get("/usage")
    assert r.status_code == 200
    data = r.json()
    assert "provider" in data
    assert "today_cost_usd" in data
    assert "by_tier" in data


def test_health_reports_provider(client):
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert "provider" in data
    assert "today_cost_usd" in data
