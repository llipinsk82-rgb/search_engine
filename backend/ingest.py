from __future__ import annotations

from dataclasses import asdict, dataclass
import time
from pathlib import Path

from backend.index import (
    ProviderSyncStats,
    delete_provider_state,
    get_provider_state,
    merge_provider_items,
    replace_provider_items,
    set_provider_state,
)
from backend.providers.base import SearchProvider
from backend.settings import DB_PATH


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


@dataclass(slots=True)
class BackfillRun:
    provider: str
    batches: int
    fetched: int
    complete: bool
    error: str | None = None


async def backfill_many(
    providers: list[SearchProvider],
    *,
    batch_size: int = 5000,
    batches_per_provider: int = 1,
    max_seconds: float | None = None,
    path: Path = DB_PATH,
) -> list[BackfillRun]:
    """Backfill incremental paged providers fairly within a shared time budget.

    Providers are processed one batch at a time in round-robin order. A failed
    provider is isolated from the others, while each successful batch advances
    its own durable cursor through :func:`backfill_provider`. The time budget is
    checked between batches, so an in-flight network request is never cancelled
    halfway through a page.
    """
    if batch_size < 1 or batches_per_provider < 1:
        raise ValueError("batch_size and batches_per_provider must be positive")
    if max_seconds is not None and max_seconds < 0:
        raise ValueError("max_seconds must be non-negative")

    started = time.monotonic()
    states = {
        provider.name: BackfillRun(
            provider=provider.name, batches=0, fetched=0, complete=False
        )
        for provider in providers
    }
    active = sorted(
        providers,
        key=lambda provider: int(getattr(provider, "backfill_priority", 100)),
    )

    for _ in range(batches_per_provider):
        if not active:
            break
        next_active: list[SearchProvider] = []
        for provider in active:
            if max_seconds is not None and time.monotonic() - started >= max_seconds:
                return list(states.values())
            state = states[provider.name]
            try:
                provider_batch_size = (
                    getattr(provider, "backfill_batch_size", None) or batch_size
                )
                remaining_seconds = (
                    None
                    if max_seconds is None
                    else max(0.0, max_seconds - (time.monotonic() - started))
                )
                results = await backfill_provider(
                    provider,
                    batch_size=int(provider_batch_size),
                    batches=1,
                    max_seconds=remaining_seconds,
                    path=path,
                )
            except Exception as exc:
                state.error = str(exc)
                continue

            if not results:
                state.complete = True
                continue

            state.batches += 1
            state.fetched += sum(result.fetched for result in results)
            next_active.append(provider)
        active = next_active

    return list(states.values())


async def backfill_provider(
    provider: SearchProvider,
    *,
    batch_size: int = 5000,
    batches: int = 1,
    reset: bool = False,
    max_seconds: float | None = None,
    path: Path = DB_PATH,
) -> list[ProviderSyncStats]:
    """Resume an incremental sitemap backfill from a persisted record cursor.

    Cursor advancement happens only after a successful merge. Replaying a batch
    after a crash is safe because item ids are deterministic upserts.
    """
    collect_page = getattr(provider, "collect_page", None)
    if collect_page is None or not callable(collect_page):
        raise ValueError(f"provider {provider.name!r} does not support paged backfill")
    if provider.sync_mode != "incremental":
        raise ValueError("backfill requires an incremental provider")
    if batch_size < 1 or batches < 1:
        raise ValueError("batch_size and batches must be positive")

    state_key = "backfill_cursor"
    if reset:
        delete_provider_state(provider.name, state_key, path=path)
    raw_cursor = get_provider_state(provider.name, state_key, path=path)
    cursor = int(raw_cursor or "0")
    max_records = getattr(provider, "backfill_max_records", None)
    results: list[ProviderSyncStats] = []
    started = time.monotonic()
    collect_page_bounded = getattr(provider, "collect_page_bounded", None)

    for _ in range(batches):
        if max_seconds is not None and time.monotonic() - started >= max_seconds:
            break
        if max_records is not None and cursor >= int(max_records):
            break
        effective_batch_size = batch_size
        if max_records is not None:
            effective_batch_size = min(
                batch_size,
                max(1, int(max_records) - cursor),
            )
        remaining_seconds = (
            None
            if max_seconds is None
            else max(0.0, max_seconds - (time.monotonic() - started))
        )
        if remaining_seconds is not None and callable(collect_page_bounded):
            items, next_cursor = await collect_page_bounded(
                offset=cursor,
                limit=effective_batch_size,
                max_seconds=remaining_seconds,
            )
        else:
            items, next_cursor = await collect_page(
                offset=cursor,
                limit=effective_batch_size,
            )
        if next_cursor <= cursor:
            break
        if items:
            result = merge_provider_items(provider.name, items, path=path)
            results.append(result)
        consumed = next_cursor - cursor
        cursor = next_cursor
        set_provider_state(provider.name, state_key, str(cursor), path=path)
        if consumed < effective_batch_size:
            break

    return results
