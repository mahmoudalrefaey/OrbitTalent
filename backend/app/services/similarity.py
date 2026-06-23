"""Deterministic similarity engine (no embeddings).

g0i.ai exposes no embedding models, so candidate↔job and candidate↔candidate
similarity uses lexical signals instead of vectors:

  similarity = α · BM25(CV vs query/JD)  +  β · weighted_skill_overlap

- **BM25** (Okapi) is classic IR ranking — pure Python, no model, no cost.
  A small corpus is built per request (the job's candidate CVs), and each CV is
  scored against the query (a free-text search string or the JD/criteria text).
- **Skill overlap** reuses `keyword_matcher` so the job's required/preferred
  skills weight the score toward genuinely matching candidates.

All functions are pure and unit-testable offline. Used by: cascade Tier-1 gate,
advanced free-text search ranking, and "similar candidates" in comparison.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from app.config import get_settings
from app.services import keyword_matcher

settings = get_settings()

# BM25 free parameters (standard defaults).
_K1 = 1.5
_B = 0.75
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+.#-]*")


def tokenize(text: str) -> list[str]:
    """Lowercase word/skill tokens. Keeps c++, c#, node.js, .net intact."""
    return _TOKEN_RE.findall(text.lower())


class BM25:
    """Okapi BM25 over a fixed corpus of documents (list of token lists)."""

    def __init__(self, corpus: list[list[str]]) -> None:
        self.corpus = corpus
        self.n = len(corpus)
        self.doc_len = [len(d) for d in corpus]
        self.avgdl = (sum(self.doc_len) / self.n) if self.n else 0.0
        self.freqs = [Counter(d) for d in corpus]
        # Document frequency per term.
        df: Counter = Counter()
        for d in corpus:
            df.update(set(d))
        # BM25+ idf (always positive).
        self.idf = {
            t: math.log(1 + (self.n - n + 0.5) / (n + 0.5)) for t, n in df.items()
        }

    def score(self, query_tokens: list[str], index: int) -> float:
        if self.avgdl == 0:
            return 0.0
        freq = self.freqs[index]
        dl = self.doc_len[index]
        score = 0.0
        for t in query_tokens:
            if t not in freq:
                continue
            tf = freq[t]
            idf = self.idf.get(t, 0.0)
            denom = tf + _K1 * (1 - _B + _B * dl / self.avgdl)
            score += idf * (tf * (_K1 + 1)) / denom
        return score

    def scores(self, query_tokens: list[str]) -> list[float]:
        return [self.score(query_tokens, i) for i in range(self.n)]


def _normalize_scores(raw: list[float]) -> list[float]:
    """Scale a list of BM25 scores to 0..1 by the max (rank-preserving)."""
    hi = max(raw, default=0.0)
    if hi <= 0:
        return [0.0] * len(raw)
    return [r / hi for r in raw]


def skill_overlap(
    cv_text: str, required: list[str], preferred: list[str]
) -> float:
    """0..1 weighted skill coverage — required skills count double preferred."""
    req = keyword_matcher.match_keywords(cv_text, required)
    pref = keyword_matcher.match_keywords(cv_text, preferred)
    req_total, pref_total = len(required), len(preferred)
    if req_total == 0 and pref_total == 0:
        return 0.0
    # Weighted: required worth 2x preferred.
    num = 2 * len(req.matched) + len(pref.matched)
    den = 2 * req_total + pref_total
    return num / den if den else 0.0


def rank_candidates(
    query: str,
    candidate_texts: list[str],
    *,
    required: list[str] | None = None,
    preferred: list[str] | None = None,
    alpha: float = 0.6,
    beta: float = 0.4,
) -> list[float]:
    """Return a 0..100 similarity score per candidate for a free-text query.

    Blends normalized BM25 (text relevance) with weighted skill overlap. When
    no skills are supplied, β collapses and it's pure BM25.
    """
    required = required or []
    preferred = preferred or []
    corpus = [tokenize(t) for t in candidate_texts]
    bm25 = BM25(corpus)
    bm_norm = _normalize_scores(bm25.scores(tokenize(query)))

    use_skills = bool(required or preferred)
    a, b = (alpha, beta) if use_skills else (1.0, 0.0)

    out: list[float] = []
    for i, text in enumerate(candidate_texts):
        skill = skill_overlap(text, required, preferred) if use_skills else 0.0
        out.append(round(100.0 * (a * bm_norm[i] + b * skill), 1))
    return out


def job_similarity(
    cv_text: str,
    jd_text: str,
    required: list[str],
    preferred: list[str],
) -> float:
    """0..100 similarity of ONE cv against the JD — the cascade Tier-1 signal.

    Uses the CV as a single-doc corpus scored against the JD text, blended with
    skill overlap. Deterministic, zero-cost.
    """
    if not cv_text.strip():
        return 0.0
    corpus = [tokenize(cv_text)]
    bm25 = BM25(corpus)
    # Single-doc corpus → BM25 is unbounded; squash to 0..1 via a soft cap.
    raw = bm25.score(tokenize(jd_text), 0)
    bm_norm = raw / (raw + 5.0)  # diminishing returns; ~0.5 at raw=5
    skill = skill_overlap(cv_text, required, preferred)
    return round(100.0 * (0.6 * bm_norm + 0.4 * skill), 1)
