from __future__ import annotations

import asyncio
import re
from collections import defaultdict

from backend.index import count_items, indexed_providers, search_items
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


async def _live_search(
    query: str,
    *,
    provider: str | None,
    quality: str | None,
    min_duration: int | None,
    max_duration: int | None,
    offset: int,
    limit: int,
) -> tuple[list[SearchItem], list[str], bool]:
    selected: list[SearchProvider] = [
        item for item in PROVIDERS if provider is None or item.name == provider
    ]

    target = offset + limit + 1
    provider_limit = max(target * 2, limit)

    batches = await asyncio.gather(
        *(item.search(query, limit=provider_limit) for item in selected),
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

    collapsed = _collapse(flat, target)
    page, has_more = _slice_page(collapsed, offset=offset, limit=limit)
    return page, used_providers, has_more


async def search_all(
    query: str,
    *,
    provider: str | None = None,
    quality: str | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    offset: int = 0,
    limit: int = 40,
) -> tuple[list[SearchItem], list[str], bool]:
    indexed_names = indexed_providers() if count_items() > 0 else []
    can_use_index = bool(indexed_names) and (
        provider is None or provider in indexed_names
    )

    if can_use_index:
        target = offset + limit + 1
        indexed = search_items(
            query,
            provider=provider,
            quality=quality,
            min_duration=min_duration,
            max_duration=max_duration,
            limit=max(target * 2, limit),
        )
        collapsed = _collapse(indexed, target)
        page, has_more = _slice_page(collapsed, offset=offset, limit=limit)

        providers = indexed_names
        if provider:
            providers = [name for name in providers if name == provider]
        return page, providers, has_more

    return await _live_search(
        query,
        provider=provider,
        quality=quality,
        min_duration=min_duration,
        max_duration=max_duration,
        offset=offset,
        limit=limit,
    )
