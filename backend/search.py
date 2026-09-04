from __future__ import annotations

import re
from collections import defaultdict

from backend.index import count_search_items, indexed_providers, search_items
from backend.models import SearchItem, SourceVariant

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


def _collapse(items: list[SearchItem], limit: int) -> list[SearchItem]:
    grouped: dict[tuple[str, int], list[SearchItem]] = defaultdict(list)
    for item in items:
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
    return collapsed[:limit]


def _slice_page(
    items: list[SearchItem],
    *,
    offset: int,
    limit: int,
) -> tuple[list[SearchItem], bool]:
    end = offset + limit
    return items[offset:end], len(items) > end


async def search_all(
    query: str,
    *,
    provider: str | None = None,
    quality: str | None = None,
    age_check: str | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    offset: int = 0,
    limit: int = 40,
    allowed_providers: set[str] | None = None,
    exclude_ids: set[str] | None = None,
) -> tuple[list[SearchItem], list[str], bool, int]:
    indexed = set(indexed_providers())
    allowed = indexed if allowed_providers is None else indexed & allowed_providers
    if provider is not None:
        allowed &= {provider}

    total = count_search_items(
        query,
        provider=provider,
        quality=quality,
        age_check=age_check,
        min_duration=min_duration,
        max_duration=max_duration,
        allowed_providers=allowed,
    )
    items = search_items(
        query,
        provider=provider,
        quality=quality,
        age_check=age_check,
        min_duration=min_duration,
        max_duration=max_duration,
        allowed_providers=allowed,
        exclude_ids=exclude_ids,
        offset=offset,
        limit=limit,
    )
    used = sorted(allowed)
    has_more = total > offset + len(items)
    return items, used, has_more, total
