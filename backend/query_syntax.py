from __future__ import annotations

from dataclasses import dataclass
import re


_token_re = re.compile(r"\w+", re.UNICODE)
_plus_re = re.compile(r"\s*\+\s*")


@dataclass(frozen=True, slots=True)
class ParsedSearchQuery:
    provider_query: str
    tokens: tuple[str, ...]
    required_tokens: tuple[str, ...]
    explicit_and: bool


def parse_search_query(query: str) -> ParsedSearchQuery:
    raw = " ".join(query.strip().split())
    explicit_and = "+" in raw
    provider_query = _plus_re.sub(" ", raw) if explicit_and else raw
    provider_query = " ".join(provider_query.split())
    tokens = tuple(dict.fromkeys(_token_re.findall(provider_query.casefold())))
    return ParsedSearchQuery(
        provider_query=provider_query,
        tokens=tokens,
        required_tokens=tokens if explicit_and else (),
        explicit_and=explicit_and,
    )
