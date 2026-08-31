from __future__ import annotations

import argparse
import asyncio

from backend.index import count_items, initialize, provider_counts
from backend.ingest import sync_provider
from backend.providers import PROVIDERS
from backend.providers.base import SearchProvider


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


async def _sync_all(limit: int, allow_empty: bool) -> None:
    failures = 0
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


if __name__ == "__main__":
    main()
