"""Shared pytest fixtures: synthetic CV files for parser/scorer tests.

Also sets DATABASE_URL to a temp SQLite file and ANTHROPIC_API_KEY="" BEFORE
any app module is imported, so the engine binds to the test DB. This runs at
import time (pytest imports conftest first), guaranteeing it beats app imports
inside individual test modules.
"""
import os
import tempfile

import pytest

import io  # noqa: E402  (after the env setup above, intentionally)

_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db", prefix="orbittalent_test_")
os.close(_TEST_DB_FD)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ.setdefault("ANTHROPIC_API_KEY", "")


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
