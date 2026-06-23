"""Tests for the deterministic BM25 + skill-overlap similarity engine."""
from app.services import similarity


def test_tokenize_keeps_symbol_tokens():
    toks = similarity.tokenize("Python, C++ and Node.js — .NET / C#")
    assert "c++" in toks
    assert "node.js" in toks
    assert "python" in toks


def test_bm25_ranks_relevant_doc_higher():
    docs = [
        "python fastapi backend rest api postgres",
        "graphic designer photoshop illustrator branding",
        "python data science pandas numpy",
    ]
    corpus = [similarity.tokenize(d) for d in docs]
    bm = similarity.BM25(corpus)
    scores = bm.scores(similarity.tokenize("python fastapi backend api"))
    # Doc 0 is the clear match; the designer doc should score ~0.
    assert scores[0] > scores[2] > scores[1]
    assert scores[1] == 0.0


def test_skill_overlap_weights_required_double():
    cv = "Experienced in Python and FastAPI. Built REST APIs."
    # All required matched, no preferred → 1.0
    assert similarity.skill_overlap(cv, ["Python", "FastAPI"], []) == 1.0
    # Half of required matched → 0.5
    assert similarity.skill_overlap(cv, ["Python", "Rust"], []) == 0.5


def test_rank_candidates_orders_by_relevance():
    cands = [
        "Senior Python FastAPI backend engineer, AWS, PostgreSQL.",
        "Pastry chef, ten years baking bread and cakes.",
        "Junior python developer, some Django.",
    ]
    scores = similarity.rank_candidates(
        "python backend engineer fastapi aws",
        cands,
        required=["Python", "FastAPI", "AWS"],
    )
    assert scores[0] == max(scores)
    assert scores[1] == min(scores)
    assert all(0 <= s <= 100 for s in scores)


def test_job_similarity_range_and_discrimination():
    jd = "Backend engineer with Python, FastAPI, AWS, PostgreSQL."
    good = "7 years Python FastAPI AWS PostgreSQL backend microservices."
    bad = "Marketing manager, social media, branding, copywriting."
    s_good = similarity.job_similarity(good, jd, ["Python", "FastAPI", "AWS"], [])
    s_bad = similarity.job_similarity(bad, jd, ["Python", "FastAPI", "AWS"], [])
    assert 0 <= s_bad < s_good <= 100
    assert similarity.job_similarity("", jd, [], []) == 0.0
