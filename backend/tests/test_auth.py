"""Auth + tenant-isolation tests."""
import pytest
from fastapi.testclient import TestClient

from tests.conftest import reset_database


@pytest.fixture
def app_client():
    """Unauthenticated client with a clean schema (no auto-login)."""
    from app.main import app

    reset_database()
    with TestClient(app) as c:
        yield c


def test_register_sets_cookie_and_me_works(app_client):
    r = app_client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "password123", "name": "A"},
    )
    assert r.status_code == 201
    assert "ot_session" in r.cookies or "ot_session" in app_client.cookies
    body = r.json()
    assert body["email"] == "a@example.com"
    assert "hashed_password" not in body  # never leak the hash

    me = app_client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"


def test_duplicate_email_conflicts(app_client):
    payload = {"email": "dup@example.com", "password": "password123"}
    assert app_client.post("/auth/register", json=payload).status_code == 201
    # Same email again -> 409 (case-insensitive).
    r = app_client.post(
        "/auth/register",
        json={"email": "DUP@example.com", "password": "password123"},
    )
    assert r.status_code == 409


def test_short_password_rejected(app_client):
    r = app_client.post(
        "/auth/register",
        json={"email": "x@example.com", "password": "short"},
    )
    assert r.status_code == 422  # pydantic min_length


def test_login_wrong_password_401(app_client):
    app_client.post(
        "/auth/register",
        json={"email": "b@example.com", "password": "password123"},
    )
    app_client.post("/auth/logout")
    r = app_client.post(
        "/auth/login", json={"email": "b@example.com", "password": "wrongpass"}
    )
    assert r.status_code == 401


def test_login_unknown_email_401(app_client):
    r = app_client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "password123"}
    )
    assert r.status_code == 401


def test_protected_endpoint_requires_auth(app_client):
    # Fresh client, no cookie -> 401 on app endpoints.
    assert app_client.get("/jobs").status_code == 401
    # After register, the cookie is set -> 200.
    app_client.post(
        "/auth/register",
        json={"email": "c@example.com", "password": "password123"},
    )
    assert app_client.get("/jobs").status_code == 200


def test_logout_clears_session(app_client):
    app_client.post(
        "/auth/register",
        json={"email": "d@example.com", "password": "password123"},
    )
    assert app_client.get("/auth/me").status_code == 200
    app_client.post("/auth/logout")
    assert app_client.get("/auth/me").status_code == 401


def test_tenant_isolation_between_users(app_client):
    # User A creates a job.
    app_client.post(
        "/auth/register",
        json={"email": "owner@example.com", "password": "password123"},
    )
    job_id = app_client.post(
        "/jobs", json={"title": "Secret Role", "jd_text": "x"}
    ).json()["id"]
    assert app_client.get("/jobs").json()  # A sees their job

    # User B logs in (replaces the cookie) and must NOT see or access A's job.
    app_client.post(
        "/auth/register",
        json={"email": "intruder@example.com", "password": "password123"},
    )
    assert app_client.get("/jobs").json() == []  # B's list is empty
    assert app_client.get(f"/jobs/{job_id}").status_code == 404  # IDOR-safe
    assert app_client.get(f"/jobs/{job_id}/candidates").status_code == 404
    assert app_client.get(f"/jobs/{job_id}/analytics").status_code == 404
