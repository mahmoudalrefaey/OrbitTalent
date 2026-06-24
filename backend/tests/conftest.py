"""Shared pytest fixtures and test environment setup.

Tests run against PostgreSQL. Point them at a throwaway database with
TEST_DATABASE_URL (defaults to a local `orbittalent_test`). The environment is
configured here, at import time, before any app module is imported, so the
engine binds to the test database.
"""
import os

import pytest

import io  # noqa: E402  (after the env setup below, intentionally)

# Dedicated test database — never the dev/prod one. Override with TEST_DATABASE_URL.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/orbittalent_test",
)
# No real key in tests — extract-criteria must 503, and LLM is patched per-test.
os.environ.setdefault("LLM_API_KEY", "")
# Deterministic signing secret for auth tests.
os.environ.setdefault("JWT_SECRET", "test-secret-key")
# Disable per-IP rate limiting — the suite makes many auth calls from one client.
os.environ["RATE_LIMIT_ENABLED"] = "false"
# Pin cascade thresholds so tests are independent of the developer's .env tuning.
# A permissive Tier-1 keeps the "candidate gets scored" assertions stable; the
# Tier-1 gate firing is covered explicitly in test_cascade.py with crafted CVs.
os.environ["TIER0_MIN_COVERAGE"] = "0.05"
os.environ["TIER1_MIN_SIMILARITY"] = "0.0"
os.environ["TIER2_ACCEPT_CONFIDENCE"] = "0.75"
os.environ["TIER3_ESCALATE_MATCH_PCT"] = "70"


CLEAN_CV_TEXT = """\
Jane Developer
jane.developer@example.com | +1 (555) 123-4567 | San Francisco, CA

SUMMARY
Senior software engineer with eight years of experience building reliable,
scalable backend systems and leading small engineering teams. Passionate about
clean architecture, developer experience, and shipping pragmatic solutions.

PROFESSIONAL EXPERIENCE
Senior Software Engineer, Acme Corp (2019 - present)
- Built scalable backend services in Python and FastAPI serving millions of
  requests per day with strong reliability guarantees.
- Led the migration from a legacy monolith to PostgreSQL and AWS, cutting
  infrastructure cost by 30 percent and improving uptime.
- Mentored a team of five engineers on React and TypeScript best practices,
  establishing code review standards and CI/CD pipelines.
- Designed and maintained REST APIs consumed by internal and external clients.

Software Engineer, Beta Inc (2016 - 2019)
- Developed REST APIs and microservices, containerized with Docker and
  orchestrated on Kubernetes.
- Implemented automated testing and continuous integration with Git workflows.
- Collaborated with product and design on feature delivery across two teams.

EDUCATION
B.Sc. Computer Science, State University (2016)
Graduated with honors; coursework in algorithms, databases, and distributed
systems.

SKILLS
Python, FastAPI, JavaScript, React, TypeScript, PostgreSQL, AWS, Docker,
Kubernetes, machine learning, REST APIs, Git, CI/CD, agile methodologies.
"""


def reset_database() -> None:
    """Drop and recreate the public schema so each test starts clean.

    `DROP SCHEMA ... CASCADE` clears tables, enum types, and sequences in one
    shot, which `Base.metadata.drop_all` would not (it leaves PostgreSQL enum
    types behind). `init_db` then recreates everything from the model metadata.
    """
    from sqlalchemy import text

    from app.db import engine, init_db

    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    init_db()


@pytest.fixture
def clean_cv_text() -> str:
    return CLEAN_CV_TEXT


@pytest.fixture
def clean_cv_txt_bytes() -> bytes:
    return CLEAN_CV_TEXT.encode("utf-8")


@pytest.fixture
def clean_cv_docx_bytes() -> bytes:
    from docx import Document

    doc = Document()
    for line in CLEAN_CV_TEXT.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.fixture
def sparse_cv_txt_bytes() -> bytes:
    # Almost no content, no contact info, no sections.
    return b"John\nLooking for a job.\nHardworking."
