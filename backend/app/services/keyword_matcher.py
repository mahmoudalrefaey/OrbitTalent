"""Keyword matching: which criteria keywords appear in the CV text.

Normalizes both sides (lowercase, punctuation, common aliases) and does
word-boundary-aware substring matching so 'c++' / 'node.js' / '.NET' work.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Minimal alias map — extend over time. Maps a canonical keyword to extra
# surface forms that should also count as a match.
_ALIASES: dict[str, list[str]] = {
    "javascript": ["js", "ecmascript"],
    "typescript": ["ts"],
    "node.js": ["node", "nodejs"],
    "postgresql": ["postgres", "psql"],
    "kubernetes": ["k8s"],
    "amazon web services": ["aws"],
    "google cloud platform": ["gcp"],
    "c#": ["c sharp", "csharp", ".net", "dotnet"],
    "c++": ["cpp", "cplusplus"],
    "machine learning": ["ml"],
    "natural language processing": ["nlp"],
}


@dataclass
class KeywordMatch:
    matched: list[str]
    missing: list[str]

    @property
    def coverage(self) -> float:
        total = len(self.matched) + len(self.missing)
        return round(len(self.matched) / total, 3) if total else 0.0


def _normalize(text: str) -> str:
    # Collapse whitespace; keep + # . for tokens like c++, c#, node.js.
    return re.sub(r"\s+", " ", text.lower())


def _surface_forms(keyword: str) -> list[str]:
    k = keyword.lower().strip()
    forms = [k, *_ALIASES.get(k, [])]
    # Also fold known aliases back to canonical: if the keyword IS an alias.
    for canonical, aliases in _ALIASES.items():
        if k in aliases:
            forms.append(canonical)
            forms.extend(aliases)
    return list(dict.fromkeys(f for f in forms if f))


def _contains(haystack: str, needle: str) -> bool:
    needle = needle.strip()
    if not needle:
        return False
    # Word-boundary match where the token is alphanumeric; plain substring
    # for tokens containing symbols (c++, c#, .net) which \b handles poorly.
    if re.fullmatch(r"[a-z0-9 ]+", needle):
        return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None
    return needle in haystack


def match_keywords(cv_text: str, keywords: list[str]) -> KeywordMatch:
    """Return matched/missing split for the given keyword list."""
    hay = _normalize(cv_text)
    matched: list[str] = []
    missing: list[str] = []
    for kw in keywords:
        if not kw or not kw.strip():
            continue
        if any(_contains(hay, form) for form in _surface_forms(kw)):
            matched.append(kw)
        else:
            missing.append(kw)
    return KeywordMatch(matched=matched, missing=missing)
