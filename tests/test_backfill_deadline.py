from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.ingest import backfill_many, backfill_provider
from backend.models import SearchItem
from backend.providers.base import SearchProvider


class BoundedProvider(SearchProvider):
    name = "bounded"
    sync_mode = "incremental"

    def __init__(self) -> None:
        self.budgets: list[float] = []

    async def search(self, query: str, limit: int = 40) -> list[SearchItem]:
        return []

    async def collect_page(self, *, offset: int, limit: int):
        raise AssertionError("unbounded collector should not be used when budget is supplied")

    async def collect_page_bounded(
        self,
        *,
        offset: int,
        limit: int,
        max_seconds: float,
    ):
        self.budgets.append(max_seconds)
        item = SearchItem(
            id="one",
            provider=self.name,
            title="One",
            url="https://example.invalid/one",
            tags=[],
        )
        return ([item] if offset == 0 else []), (1 if offset == 0 else offset)


class BackfillDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_backfill_provider_passes_remaining_budget_to_bounded_collector(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = BoundedProvider()
            await backfill_provider(
                provider,
                batch_size=10,
                batches=1,
                max_seconds=5.0,
                path=Path(directory) / "db.sqlite",
            )
            self.assertEqual(len(provider.budgets), 1)
            self.assertGreater(provider.budgets[0], 0)
            self.assertLessEqual(provider.budgets[0], 5.0)

    async def test_backfill_many_passes_shared_budget_downstream(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = BoundedProvider()
            await backfill_many(
                [provider],
                batch_size=10,
                batches_per_provider=1,
                max_seconds=5.0,
                path=Path(directory) / "db.sqlite",
            )
            self.assertTrue(provider.budgets)
            self.assertGreater(provider.budgets[0], 0)
            self.assertLessEqual(provider.budgets[0], 5.0)


if __name__ == "__main__":
    unittest.main()
