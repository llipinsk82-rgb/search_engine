from __future__ import annotations

import re
from typing import Literal


ContentClass = Literal["amateur", "studio", "unknown"]

_AMATEUR_TOKENS = frozenset({"amateur", "homemade", "user generated"})
_STUDIO_TOKENS = frozenset({"studio", "professional", "production"})
_SPACE_RE = re.compile(r"\s+")


def _normalize_token(value: str) -> str:
    return _SPACE_RE.sub(" ", value.strip().casefold().replace("-", " "))


def classify_content(*, tags: list[str], studio: str | None) -> ContentClass:
    normalized_tags = {_normalize_token(tag) for tag in tags if tag.strip()}
    amateur_signal = bool(normalized_tags & _AMATEUR_TOKENS)
    studio_signal = bool(normalized_tags & _STUDIO_TOKENS) or bool(studio and studio.strip())

    if amateur_signal and studio_signal:
        return "unknown"
    if amateur_signal:
        return "amateur"
    if studio_signal:
        return "studio"
    return "unknown"
