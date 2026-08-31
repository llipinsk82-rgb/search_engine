from __future__ import annotations

from dataclasses import asdict

from backend.index import (
    ProviderSyncStats,
    merge_provider_items,
    replace_provider_items,
)
from backend.providers.base import SearchProvider


async def sync_provider(
    provider: SearchProvider,
    *,
    limit: int = 1000,
    allow_empty: bool = False,
) -> ProviderSyncStats:
    """Fetch first, then publish according to the provider sync mode."""
    items = await provider.collect(limit=limit)

    if provider.sync_mode == "incremental":
        return merge_provider_items(
            provider.name,
            items,
            allow_empty=allow_empty,
        )

    if provider.sync_mode == "snapshot":
        return replace_provider_items(
            provider.name,
            items,
            allow_empty=allow_empty,
        )

    raise ValueError(f"unknown provider sync_mode: {provider.sync_mode!r}")


def sync_result_dict(result: ProviderSyncStats) -> dict[str, object]:
    return asdict(result)
