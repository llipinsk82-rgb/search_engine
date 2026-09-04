from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from backend.importer import load_jsonl
from backend.index import (
    count_items,
    deactivate_provider,
    initialize,
    provider_counts,
    replace_provider_items,
)
from backend.ingest import backfill_many, backfill_provider, sync_provider
from backend.provider_probe import format_probe, probe_provider
from backend.providers import PROVIDERS
from backend.providers.base import SearchProvider
from backend.providers.sitemap import SitemapProvider


def _provider_by_name(name: str) -> SearchProvider:
    provider = next((item for item in PROVIDERS if item.name == name), None)
    if provider is None:
        known = ", ".join(sorted(item.name for item in PROVIDERS)) or "(none)"
        raise SystemExit(f"unknown provider {name!r}; known: {known}")
    return provider


async def _sync_one(name: str, limit: int, allow_empty: bool) -> None:
    provider = _provider_by_name(name)
    result = await sync_provider(
        provider,
        limit=limit,
        allow_empty=allow_empty,
    )
    print(
        f"{result.provider}: fetched={result.fetched} "
        f"active_before={result.active_before} "
        f"active_after={result.active_after} "
        f"deactivated={result.deactivated}"
    )


async def _backfill_one(name: str, batch_size: int, batches: int, reset: bool) -> None:
    provider = _provider_by_name(name)
    results = await backfill_provider(
        provider,
        batch_size=batch_size,
        batches=batches,
        reset=reset,
    )
    if not results:
        print(f"{provider.name}: backfill complete (no more records)")
        return
    for result in results:
        print(
            f"{result.provider}: fetched={result.fetched} "
            f"active_before={result.active_before} "
            f"active_after={result.active_after}"
        )


async def _backfill_all(
    batch_size: int,
    batches_per_provider: int,
    max_seconds: float | None,
) -> None:
    providers = [
        provider
        for provider in PROVIDERS
        if provider.sync_mode == "incremental"
        and callable(getattr(provider, "collect_page", None))
    ]
    if not providers:
        raise SystemExit("no paged incremental providers configured")

    runs = await backfill_many(
        providers,
        batch_size=batch_size,
        batches_per_provider=batches_per_provider,
        max_seconds=max_seconds,
    )
    failures = 0
    for run in runs:
        status = "complete" if run.complete else "paused"
        if run.error:
            failures += 1
            status = f"ERROR {run.error}"
        print(
            f"{run.provider}: batches={run.batches} fetched={run.fetched} "
            f"status={status}"
        )
    if failures:
        raise SystemExit(1)


async def _probe_one(provider: SearchProvider, limit: int) -> None:
    result, items = await probe_provider(provider, limit=limit)
    print(format_probe(result, items))


async def _probe_sitemap(
    name: str,
    sitemap_url: str,
    limit: int,
    obey_robots: bool,
) -> None:
    provider = SitemapProvider(
        name=name,
        sitemap_url=sitemap_url,
        max_pages=max(1, limit),
        delay_seconds=0.05,
        timeout_seconds=15.0,
        obey_robots=obey_robots,
        sync_mode="incremental",
    )
    await _probe_one(provider, limit)


async def _sync_all(limit: int, allow_empty: bool) -> None:
    failures = 0
    provider_names = {provider.name for provider in PROVIDERS}
    if "demo" not in provider_names:
        removed = deactivate_provider("demo")
        if removed:
            print(f"demo: deactivated={removed} (production providers configured)")

    for provider in PROVIDERS:
        try:
            result = await sync_provider(
                provider,
                limit=limit,
                allow_empty=allow_empty,
            )
        except Exception as exc:
            failures += 1
            print(f"{provider.name}: ERROR {exc}")
            continue

        print(
            f"{result.provider}: fetched={result.fetched} "
            f"active_before={result.active_before} "
            f"active_after={result.active_after} "
            f"deactivated={result.deactivated}"
        )

    if failures:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(prog="search-engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")
    subparsers.add_parser("providers")
    subparsers.add_parser("stats")

    seed = subparsers.add_parser("seed-demo")
    seed.add_argument("--limit", type=int, default=1000)

    sync = subparsers.add_parser("sync")
    sync.add_argument("provider")
    sync.add_argument("--limit", type=int, default=1000)
    sync.add_argument("--allow-empty", action="store_true")

    sync_all = subparsers.add_parser("sync-all")
    sync_all.add_argument("--limit", type=int, default=1000)
    sync_all.add_argument("--allow-empty", action="store_true")

    backfill = subparsers.add_parser("backfill")
    backfill.add_argument("provider")
    backfill.add_argument("--batch-size", type=int, default=5000)
    backfill.add_argument("--batches", type=int, default=1)
    backfill.add_argument("--reset", action="store_true")

    backfill_all = subparsers.add_parser("backfill-all")
    backfill_all.add_argument("--batch-size", type=int, default=5000)
    backfill_all.add_argument("--batches-per-provider", type=int, default=1)
    backfill_all.add_argument("--max-seconds", type=float)

    probe = subparsers.add_parser("probe")
    probe.add_argument("provider")
    probe.add_argument("--limit", type=int, default=5)

    probe_sitemap = subparsers.add_parser("probe-sitemap")
    probe_sitemap.add_argument("name")
    probe_sitemap.add_argument("sitemap_url")
    probe_sitemap.add_argument("--limit", type=int, default=5)
    probe_sitemap.add_argument("--no-robots", action="store_true")

    import_jsonl = subparsers.add_parser("import-jsonl")
    import_jsonl.add_argument("path", type=Path)
    import_jsonl.add_argument("--provider")
    import_jsonl.add_argument("--allow-empty", action="store_true")

    args = parser.parse_args()

    if args.command == "init":
        initialize()
        print("index initialized")
        return

    if args.command == "providers":
        for provider in sorted(PROVIDERS, key=lambda item: item.name):
            print(provider.name)
        return

    if args.command == "stats":
        counts = provider_counts()
        print(f"items={count_items()}")
        for provider, count in counts.items():
            print(f"{provider}={count}")
        return

    if args.command == "seed-demo":
        asyncio.run(_sync_one("demo", args.limit, False))
        return

    if args.command == "sync":
        asyncio.run(_sync_one(args.provider, args.limit, args.allow_empty))
        return

    if args.command == "sync-all":
        asyncio.run(_sync_all(args.limit, args.allow_empty))
        return
    if args.command == "backfill":
        asyncio.run(_backfill_one(args.provider, args.batch_size, args.batches, args.reset))
        return
    if args.command == "backfill-all":
        asyncio.run(
            _backfill_all(
                args.batch_size,
                args.batches_per_provider,
                args.max_seconds,
            )
        )
        return
    if args.command == "probe":
        asyncio.run(_probe_one(_provider_by_name(args.provider), args.limit))
        return
    if args.command == "probe-sitemap":
        asyncio.run(
            _probe_sitemap(
                args.name,
                args.sitemap_url,
                args.limit,
                not args.no_robots,
            )
        )
        return

    if args.command == "import-jsonl":
        groups = load_jsonl(args.path, provider_override=args.provider)
        if not groups:
            raise SystemExit("no rows found")
        for provider, items in sorted(groups.items()):
            result = replace_provider_items(
                provider,
                items,
                allow_empty=args.allow_empty,
            )
            print(
                f"{result.provider}: fetched={result.fetched} "
                f"active_before={result.active_before} "
                f"active_after={result.active_after} "
                f"deactivated={result.deactivated}"
            )
        return


if __name__ == "__main__":
    main()
