from __future__ import annotations

from dataclasses import asdict

from backend.index import ProviderSyncStats, replace_provider_items
from backend.providers.base import SearchProvider


async def sync_provider(
    provider: SearchProvider,
    *,
    limit: int = 1000,
    allow_empty: bool = False,
) -> ProviderSyncStats:
    """Fetch first, then atomically publish the new provider snapshot."""
    items = await provider.collect(limit=limit)
    return replace_provider_items(
        provider.name,
        items,
        allow_empty=allow_empty,
    )


def sync_result_dict(result: ProviderSyncStats) -> dict[str, object]:
    return asdict(result)
