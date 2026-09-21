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

# Provider-specific evidence policy. These names are the providers for which the
# 2026-09-21 bounded audit actually observed the corresponding semantic signal.
# Untrusted metadata remains useful for display/search, but must not decide the
# Amateur/Studio filter.
_AMATEUR_TAG_PROVIDERS = frozenset({
    "brazzilmoms",
    "fpo",
    "serviporno",
    "sextubespot",
    "xcafe",
    "xgroovy",
    "xnxx",
    "xvideos",
})

# No configured provider had a separately audited exact Studio tag in v2.
_STUDIO_TAG_PROVIDERS = frozenset()

# xgroovy productionCompany points at provider channel taxonomy (for example
# /channels/brazzers/) and is therefore display metadata, not sufficient proof
# that the content itself belongs in the Studio filter. xcafe and porndoe keep
# their separately-audited item-bound production-company/producer evidence.
_STUDIO_LABEL_PROVIDERS = frozenset({"xcafe", "porndoe"})


def _normalize_token(value: str) -> str:
    return _SPACE_RE.sub(" ", value.strip().casefold().replace("-", " "))


def _normalize_provider(value: str) -> str:
    return value.strip().casefold()


def classify_content_evidence(
    *, provider: str, tags: list[str], studio: str | None
) -> ContentClassification:
    provider_key = _normalize_provider(provider)
    normalized_tags = {_normalize_token(tag) for tag in tags if tag.strip()}
    amateur_tag = (
        provider_key in _AMATEUR_TAG_PROVIDERS
        and bool(normalized_tags & _AMATEUR_TOKENS)
    )
    studio_tag = (
        provider_key in _STUDIO_TAG_PROVIDERS
        and bool(normalized_tags & _STUDIO_TOKENS)
    )
    studio_label = (
        provider_key in _STUDIO_LABEL_PROVIDERS
        and bool(studio and studio.strip())
    )

    if amateur_tag and (studio_tag or studio_label):
        return ContentClassification("unknown", "conflict")
    if amateur_tag:
        return ContentClassification("amateur", "tag_amateur")
    if studio_label:
        return ContentClassification("studio", "studio_label")
    if studio_tag:
        return ContentClassification("studio", "tag_studio")
    return ContentClassification("unknown", "none")


def classify_content(*, provider: str, tags: list[str], studio: str | None) -> ContentClass:
    return classify_content_evidence(
        provider=provider,
        tags=tags,
        studio=studio,
    ).content_class
