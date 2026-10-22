from __future__ import annotations

import re


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def query_tokens(value: str) -> list[str]:
    return _TOKEN_RE.findall(value.lower())


def contains_all_terms(value: str, terms: list[str]) -> bool:
    return set(terms).issubset(set(query_tokens(value)))
