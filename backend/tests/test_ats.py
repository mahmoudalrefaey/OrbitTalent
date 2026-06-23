"""Tests for V2 ATS endpoints: stages, bulk actions, history, search, compare,
automation, analytics expansion. Reuses the authenticated client fixture +
fake LLM from test_api.py."""
import io

from tests.test_api import _use_fake_llm, client  # noqa: F401  (fixture import)


def _make_job_with_candidate(client, cv_bytes=None, title="Backend"):
    _use_fake_llm(client)
    job_id = client.post("/jobs", json={"title": title, "jd_text": "Python"}).json()["id"]
    client.put(
        f"/jobs/{job_id}/criteria",
        json={"required_skills": ["Python"], "preferred_skills": [], "min_years": 1,
              "must_haves": [], "weights": {}},
    )
    cv = cv_bytes or (
        "Jane Dev jane@x.com +1 555 111 2222 EXPERIENCE Python developer "
        "building FastAPI services. " * 10
    ).encode()
    r = client.post(
        f"/jobs/{job_id}/candidates",
        files=[("files", ("jane.txt", io.BytesIO(cv), "text/plain"))],
    )
    return job_id, r.json()[0]["id"]


def test_thirteen_stages_accessible(client):
    job_id, cid = _make_job_with_candidate(client)
    # Move through several new ATS stages.
    for stage in ["ai_screened", "qualified", "interview_scheduled", "offer_sent", "hired"]:
        r = client.patch(f"/candidates/{cid}/stage", json={"stage": stage})
        assert r.status_code == 200, r.text
        assert r.json()["stage"] == stage


def test_delete_job_cascades_candidates_and_rules(client):
    job_id, cid = _make_job_with_candidate(client)
    # Attach an automation rule scoped to this job.
    client.post(
        "/automation-rules",
        json={
            "name": "r", "job_id": job_id,
            "trigger_json": [{"field": "overall_score", "op": "lt", "value": 1}],
            "action_json": {"type": "reject", "reason": "low_ai_score"},
        },
    )

    r = client.delete(f"/jobs/{job_id}")
    assert r.status_code == 204

    # Job, its candidate, and its rule are all gone.
    assert client.get(f"/jobs/{job_id}").status_code == 404
    assert client.get(f"/candidates/{cid}").status_code == 404
    assert client.get(f"/automation-rules?job_id={job_id}").json() == []
    assert client.get("/jobs").json() == []


def test_delete_job_is_tenant_scoped(client):
    job_id, _ = _make_job_with_candidate(client)
    # A second user must not be able to delete the first user's job.
    from tests.test_api import register_user

    register_user(client, email="intruder@example.com")  # swaps the session
    assert client.delete(f"/jobs/{job_id}").status_code == 404


def test_stage_history_recorded(client):
    job_id, cid = _make_job_with_candidate(client)
    client.patch(f"/candidates/{cid}/stage", json={"stage": "shortlisted", "reason": "looks good"})
    hist = client.get(f"/candidates/{cid}/history").json()
    # initial 'applied' event + the shortlist move (+ any automation).
    assert len(hist) >= 2
    assert hist[0]["to_stage"] == "new"
    assert any(e["to_stage"] == "shortlisted" for e in hist)


def test_reject_with_reason_and_rejected_filter(client):
    job_id, cid = _make_job_with_candidate(client)
    r = client.patch(
        f"/candidates/{cid}/stage",
        json={"stage": "rejected", "rejection_reason": "wrong_location"},
    )
    assert r.json()["stage"] == "rejected"
    assert r.json()["rejection_reason"] == "wrong_location"
    # Rejected candidates remain retrievable, filterable by stage.
    rejected = client.get(f"/jobs/{job_id}/candidates?stage=rejected").json()
    assert len(rejected) == 1 and rejected[0]["id"] == cid


def test_patch_candidate_profile_fields(client):
    job_id, cid = _make_job_with_candidate(client)
    r = client.patch(
        f"/candidates/{cid}",
        json={"country": "Germany", "city": "Berlin", "experience_years": 7.5,
              "education": "BSc CS"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["country"] == "Germany" and body["experience_years"] == 7.5


def test_bulk_reject(client):
    job_id, cid = _make_job_with_candidate(client)
    r = client.post(
        "/candidates/bulk",
        json={"candidate_ids": [cid], "action": "reject", "rejection_reason": "low_ai_score"},
    )
    assert r.status_code == 200 and r.json()["updated"] == 1
    assert client.get(f"/candidates/{cid}").json()["stage"] == "rejected"


def test_bulk_export_returns_rows(client):
    job_id, cid = _make_job_with_candidate(client)
    r = client.post("/candidates/bulk", json={"candidate_ids": [cid], "action": "export"})
    assert r.status_code == 200
    assert r.json()["candidates"][0]["id"] == cid


def test_search_structured_and_freetext(client):
    job_id, cid = _make_job_with_candidate(client)
    # Structured: by stage.
    r = client.post("/candidates/search", json={"stage": "new"})
    assert r.status_code == 200 and r.json()["total"] >= 1
    # Free-text BM25 ranking.
    r2 = client.post("/candidates/search", json={"query": "python fastapi developer"})
    assert r2.status_code == 200
    assert any(c["id"] == cid for c in r2.json()["results"])


def test_compare_requires_two_to_four(client):
    job_id, c1 = _make_job_with_candidate(client)
    # Second candidate.
    cv2 = ("Bob bob@x.com +1 555 333 4444 EXPERIENCE Python and FastAPI. " * 10).encode()
    c2 = client.post(
        f"/jobs/{job_id}/candidates",
        files=[("files", ("bob.txt", io.BytesIO(cv2), "text/plain"))],
    ).json()[0]["id"]
    r = client.get(f"/candidates/compare?ids={c1},{c2}")
    assert r.status_code == 200 and len(r.json()) == 2
    # Only one id → 400.
    assert client.get(f"/candidates/compare?ids={c1}").status_code == 400


def test_automation_rule_crud_and_auto_reject(client):
    # Create an auto-reject rule: overall_score < 6 → reject low_ai_score.
    rule = client.post(
        "/automation-rules",
        json={
            "name": "reject weak",
            "trigger_json": [{"field": "overall_score", "op": "lt", "value": 6}],
            "action_json": {"type": "reject", "reason": "low_ai_score"},
        },
    )
    assert rule.status_code == 201
    rules = client.get("/automation-rules").json()
    assert len(rules) == 1
    # Delete.
    assert client.delete(f"/automation-rules/{rule.json()['id']}").status_code == 204


def test_filtered_candidate_is_auto_rejected(client):
    """A CV with none of the required skills is filtered at Tier 0 and should
    land in the `rejected` stage (not stay in `new`)."""
    job_id, _ = _make_job_with_candidate(client)
    # CV with NO 'python' -> Tier 0 filter (no required skill matched).
    cv = (
        "Bob Baker bob@x.com +1 555 999 8888 EXPERIENCE Pastry chef making "
        "bread and cakes for ten years. " * 8
    ).encode()
    cid = client.post(
        f"/jobs/{job_id}/candidates",
        files=[("files", ("bob.txt", io.BytesIO(cv), "text/plain"))],
    ).json()[0]["id"]

    detail = client.get(f"/candidates/{cid}").json()
    assert detail["score_status"] == "filtered_out"
    assert detail["stage"] == "rejected"            # <-- auto-rejected
    assert detail["rejection_reason"] == "missing_required_skills"
    # And it shows up in the rejected list.
    rejected = client.get(f"/jobs/{job_id}/candidates?stage=rejected").json()
    assert any(c["id"] == cid for c in rejected)


def test_automation_auto_reject_fires_on_score(client):
    """An auto-reject rule (overall_score < 9) should fire on a candidate whose
    deep score is 8.0, moving them to rejected automatically on upload."""
    _use_fake_llm(client)
    job_id = client.post("/jobs", json={"title": "B", "jd_text": "Python"}).json()["id"]
    client.put(
        f"/jobs/{job_id}/criteria",
        json={"required_skills": ["Python"], "preferred_skills": [], "min_years": 1,
              "must_haves": [], "weights": {}},
    )
    # Rule: reject anyone with overall_score < 9 (fake deep_score returns 8.0).
    client.post(
        "/automation-rules",
        json={
            "name": "reject under 9",
            "job_id": job_id,
            "trigger_json": [{"field": "overall_score", "op": "lt", "value": 9}],
            "action_json": {"type": "reject", "reason": "low_ai_score"},
        },
    )
    cv = ("Jane jane@x.com +1 555 111 2222 EXPERIENCE Python FastAPI dev. " * 10).encode()
    cid = client.post(
        f"/jobs/{job_id}/candidates",
        files=[("files", ("jane.txt", io.BytesIO(cv), "text/plain"))],
    ).json()[0]["id"]

    detail = client.get(f"/candidates/{cid}").json()
    assert detail["stage"] == "rejected"
    assert detail["rejection_reason"] == "low_ai_score"


def test_automation_value_as_string_still_matches(client):
    """Rule value sent as a string (as the UI form does) must still compare
    numerically against a numeric candidate field."""
    _use_fake_llm(client)
    job_id = client.post("/jobs", json={"title": "B", "jd_text": "Python"}).json()["id"]
    client.put(
        f"/jobs/{job_id}/criteria",
        json={"required_skills": ["Python"], "preferred_skills": [], "min_years": 1,
              "must_haves": [], "weights": {}},
    )
    client.post(
        "/automation-rules",
        json={
            "name": "reject under 9 (string value)",
            "job_id": job_id,
            "trigger_json": [{"field": "overall_score", "op": "lt", "value": "9"}],
            "action_json": {"type": "reject", "reason": "low_ai_score"},
        },
    )
    cv = ("Jane jane@x.com +1 555 111 2222 EXPERIENCE Python FastAPI dev. " * 10).encode()
    cid = client.post(
        f"/jobs/{job_id}/candidates",
        files=[("files", ("jane.txt", io.BytesIO(cv), "text/plain"))],
    ).json()[0]["id"]
    assert client.get(f"/candidates/{cid}").json()["stage"] == "rejected"


def test_analytics_expansion_fields(client):
    job_id, cid = _make_job_with_candidate(client)
    client.patch(f"/candidates/{cid}/stage", json={"stage": "shortlisted"})
    a = client.get(f"/jobs/{job_id}/analytics").json()
    assert "skill_gaps" in a
    assert "funnel" in a and isinstance(a["funnel"], list)
    assert "score_distribution" in a
    assert "by_country" in a
    # Funnel includes the ordered happy-path stages.
    stages = [f["stage"] for f in a["funnel"]]
    assert "new" in stages and "hired" in stages


def test_analytics_csv_export(client):
    job_id, cid = _make_job_with_candidate(client)
    r = client.get(f"/jobs/{job_id}/analytics/export")
    assert r.status_code == 200
    assert r.text.startswith("id,")          # CSV header
    assert "jane.txt" in r.text               # the candidate row


def test_overview_dashboard(client):
    job_id, cid = _make_job_with_candidate(client)
    r = client.get("/analytics/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["total_jobs"] >= 1 and body["total_candidates"] >= 1
    assert any(j["id"] == job_id for j in body["jobs"])
