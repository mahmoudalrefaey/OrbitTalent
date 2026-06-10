"""Tests for cv_parser, ats_scorer, keyword_matcher."""
from app.services.ats_scorer import score_ats
from app.services.cv_parser import parse_cv
from app.services.keyword_matcher import match_keywords


# --------------------------- cv_parser --------------------------- #
def test_parse_txt(clean_cv_txt_bytes):
    parsed = parse_cv("jane.txt", clean_cv_txt_bytes)
    assert parsed.parse_error == ""
    assert "FastAPI" in parsed.text
    assert parsed.word_count > 50


def test_parse_docx(clean_cv_docx_bytes):
    parsed = parse_cv("jane.docx", clean_cv_docx_bytes)
    assert parsed.parse_error == ""
    assert "PostgreSQL" in parsed.text
    assert parsed.page_count == 1


def test_parse_unsupported_type():
    parsed = parse_cv("photo.png", b"\x89PNG...")
    assert parsed.parse_error != ""
    assert parsed.text == ""


def test_parse_never_raises_on_garbage():
    # Garbage bytes claiming to be a PDF should land in parse_error, not raise.
    parsed = parse_cv("broken.pdf", b"not a real pdf")
    assert parsed.parse_error != ""


# --------------------------- ats_scorer --------------------------- #
def test_ats_clean_cv_scores_high(clean_cv_txt_bytes):
    parsed = parse_cv("jane.txt", clean_cv_txt_bytes)
    result = score_ats(parsed)
    assert result.score >= 85
    assert result.issues == []  # clean CV has no issues


def test_ats_sparse_cv_scores_low(sparse_cv_txt_bytes):
    parsed = parse_cv("john.txt", sparse_cv_txt_bytes)
    result = score_ats(parsed)
    assert result.score <= 20
    assert any("text" in i.lower() or "section" in i.lower() for i in result.issues)


def test_ats_parse_error_scores_zero():
    parsed = parse_cv("photo.png", b"\x89PNG")
    result = score_ats(parsed)
    assert result.score == 0.0
    assert result.issues


def test_ats_missing_contact_info():
    text = (
        "PROFESSIONAL EXPERIENCE\n" + "Engineer doing things. " * 30
        + "\nEDUCATION\nDegree.\nSKILLS\nPython, coding, software, testing."
    )
    parsed = parse_cv("nocontact.txt", text.encode())
    result = score_ats(parsed)
    assert any("email" in i.lower() for i in result.issues)
    assert result.score < 100


# --------------------------- keyword_matcher --------------------------- #
def test_keyword_basic_match(clean_cv_text):
    result = match_keywords(clean_cv_text, ["Python", "Rust", "React"])
    assert "Python" in result.matched
    assert "React" in result.matched
    assert "Rust" in result.missing


def test_keyword_aliases(clean_cv_text):
    # CV says "AWS" and "Kubernetes"; criteria use long forms / aliases.
    result = match_keywords(clean_cv_text, ["Amazon Web Services", "k8s", "JS"])
    assert "Amazon Web Services" in result.matched   # via "aws" alias
    assert "k8s" in result.matched                   # alias of kubernetes
    assert "JS" in result.matched                    # alias of javascript


def test_keyword_symbol_tokens():
    cv = "Experienced in C++ and C# and .NET development."
    result = match_keywords(cv, ["C++", "C#", "Java"])
    assert "C++" in result.matched
    assert "C#" in result.matched
    assert "Java" in result.missing


def test_keyword_no_substring_false_positive():
    # "Java" must NOT match inside "JavaScript".
    cv = "I write JavaScript every day."
    result = match_keywords(cv, ["Java"])
    assert "Java" in result.missing


def test_keyword_coverage():
    result = match_keywords("python and react", ["python", "react", "go", "rust"])
    assert result.coverage == 0.5
