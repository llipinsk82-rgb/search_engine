from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


ContentClass = Literal["amateur", "studio", "unknown"]
ContentClassSource = Literal[
    "none",
    "tag_amateur",
    "tag_studio",
    "studio_label",
    "explicit_provider",
    "conflict",
]


@dataclass(frozen=True)
class ContentClassification:
    content_class: ContentClass
    source: ContentClassSource


_AMATEUR_TOKENS = frozenset({"amateur", "homemade", "user generated"})
_STUDIO_TOKENS = frozenset({"professional", "production"})
_SPACE_RE = re.compile(r"\s+")


def _normalize_token(value: str) -> str:
    return _SPACE_RE.sub(" ", value.strip().casefold().replace("-", " "))


def classify_content_evidence(*, tags: list[str], studio: str | None) -> ContentClassification:
    normalized_tags = {_normalize_token(tag) for tag in tags if tag.strip()}
    amateur_tag = bool(normalized_tags & _AMATEUR_TOKENS)
    studio_tag = bool(normalized_tags & _STUDIO_TOKENS)
    studio_label = bool(studio and studio.strip())

    if amateur_tag and (studio_tag or studio_label):
        return ContentClassification("unknown", "conflict")
    if amateur_tag:
        return ContentClassification("amateur", "tag_amateur")
    if studio_label:
        return ContentClassification("studio", "studio_label")
    if studio_tag:
        return ContentClassification("studio", "tag_studio")
    return ContentClassification("unknown", "none")


def classify_content(*, tags: list[str], studio: str | None) -> ContentClass:
    return classify_content_evidence(tags=tags, studio=studio).content_class
