from __future__ import annotations

import asyncio
import re
from collections import defaultdict

from backend.models import SearchItem, SourceVariant
from backend.providers import PROVIDERS
from backend.providers.base import SearchProvider

_space_re = re.compile(r"\s+")
_punct_re = re.compile(r"[^\w\s]", re.UNICODE)


def _title_key(title: str) -> str:
    value = _punct_re.sub(" ", title.lower())
    return _space_re.sub(" ", value).strip()


def _quality_rank(value: str | None) -> int:
    if not value:
        return 0
    table = {"720p": 1, "1080p": 2, "1440p": 3, "4k": 4, "8k": 5}
    return table.get(value.lower(), 0)


async def search_all(
    query: str,
    *,
    provider: str | None = None,
    quality: str | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    limit: int = 40,
) -> tuple[list[SearchItem], list[str]]:
    selected: list[SearchProvider] = [
        item for item in PROVIDERS if provider is None or item.name == provider
    ]

    batches = await asyncio.gather(
        *(item.search(query, limit=limit) for item in selected),
        return_exceptions=True,
    )

    flat: list[SearchItem] = []
    used_providers: list[str] = []
    for source, batch in zip(selected, batches):
        if isinstance(batch, Exception):
            continue
        used_providers.append(source.name)
        for item in batch:
            if quality and (item.quality or "").lower() != quality.lower():
                continue
            if min_duration is not None and (item.duration_seconds or 0) < min_duration:
                continue
            if max_duration is not None and item.duration_seconds is not None and item.duration_seconds > max_duration:
                continue
            flat.append(item)

    grouped: dict[tuple[str, int], list[SearchItem]] = defaultdict(list)
    for item in flat:
        duration_bucket = round((item.duration_seconds or 0) / 15)
        grouped[(_title_key(item.title), duration_bucket)].append(item)

    collapsed: list[SearchItem] = []
    for group in grouped.values():
        group.sort(key=lambda item: (item.score, _quality_rank(item.quality)), reverse=True)
        primary = group[0]
        primary.alternate_sources = [
            SourceVariant(provider=alt.provider, url=alt.url, quality=alt.quality)
            for alt in group[1:]
        ]
        collapsed.append(primary)

    collapsed.sort(key=lambda item: (item.score, _quality_rank(item.quality)), reverse=True)
    return collapsed[:limit], used_providers
