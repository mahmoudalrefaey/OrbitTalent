"""Deterministic ATS-readiness scoring.

Answers: "would this CV survive an automated applicant-tracking parser?"
This is independent of the job — it's about CV hygiene, not fit.
Returns a 0-100 score and a list of human-readable issues.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.cv_parser import ParsedCV

# Section headings an ATS expects to find.
_SECTION_PATTERNS = {
    "experience": r"\b(experience|employment|work history|professional background)\b",
    "education": r"\b(education|academic|qualifications?)\b",
    "skills": r"\b(skills|competenc|technologies|technical)\b",
}

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,4}\d{2,4})")


@dataclass
class ATSResult:
    score: float          # 0-100
    issues: list[str]


def score_ats(parsed: ParsedCV) -> ATSResult:
    """Score CV parse-ability. Each check deducts from a perfect 100."""
    if parsed.parse_error:
        return ATSResult(score=0.0, issues=[f"Could not parse file: {parsed.parse_error}"])

    text = parsed.text
    lower = text.lower()
    issues: list[str] = []
    score = 100.0

    # 1. There must be extractable text at all.
    if parsed.word_count < 40:
        # Distinguish "scanned/image-only" from "genuinely a stub of a CV".
        if parsed.has_images or parsed.word_count == 0:
            msg = (
                "Almost no machine-readable text extracted — the CV is likely "
                "image-based or scanned, which most ATS parsers cannot read."
            )
        else:
            msg = (
                "Very little content extracted — the CV is too short for "
                "reliable screening and is missing standard sections."
            )
        return ATSResult(score=5.0, issues=[msg])

    # 2. Contact info.
    if not _EMAIL_RE.search(text):
        score -= 20
        issues.append("No email address detected.")
    if not _PHONE_RE.search(text):
        score -= 10
        issues.append("No phone number detected.")

    # 3. Standard sections (up to 30 pts, 10 each).
    for name, pattern in _SECTION_PATTERNS.items():
        if not re.search(pattern, lower):
            score -= 10
            issues.append(f"Missing a clearly-labelled '{name}' section.")

    # 4. Length sanity (ATS dislikes extremes).
    if parsed.word_count < 120:
        score -= 10
        issues.append("Short CV (under ~120 words) — may lack detail for matching.")
    elif parsed.word_count > 1500:
        score -= 5
        issues.append("Very long CV (over ~1500 words) — consider tightening.")

    # 5. Structural hazards that break parsers.
    if parsed.has_tables:
        score -= 8
        issues.append(
            "Contains tables — multi-column tables often scramble text order in ATS parsers."
        )
    if parsed.has_images and parsed.word_count < 250:
        score -= 7
        issues.append(
            "Relies on images with little surrounding text — content inside images is invisible to ATS."
        )

    score = max(0.0, min(100.0, score))
    return ATSResult(score=round(score, 1), issues=issues)
