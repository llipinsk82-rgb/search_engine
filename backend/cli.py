from __future__ import annotations

import argparse
import asyncio

from backend.index import count_items, initialize, upsert_items
from backend.providers import PROVIDERS


async def seed_demo() -> None:
    provider = next((item for item in PROVIDERS if item.name == "demo"), None)
    if provider is None:
        raise SystemExit("demo provider is not registered")
    items = await provider.search("", limit=1000)
    written = upsert_items(items)
    print(f"indexed {written} demo items")


def main() -> None:
    parser = argparse.ArgumentParser(prog="search-engine")
    parser.add_argument("command", choices=["init", "seed-demo", "stats"])
    args = parser.parse_args()

    if args.command == "init":
        initialize()
        print("index initialized")
    elif args.command == "seed-demo":
        asyncio.run(seed_demo())
    elif args.command == "stats":
        print(f"items={count_items()}")


if __name__ == "__main__":
    main()
