from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.index import count_items, get_provider_state
from backend.ingest import backfill_provider
from backend.models import SearchItem
from backend.providers.base import SearchProvider


class _PagedProvider(SearchProvider):
    name = "paged"
    sync_mode = "incremental"

    def __init__(self) -> None:
        self.rows = [
            SearchItem(
                id=f"id-{index}",
                provider=self.name,
                title=f"Item {index}",
                url=f"https://example.com/{index}",
                tags=[],
            )
            for index in range(5)
        ]

    async def search(self, query: str, limit: int = 40) -> list[SearchItem]:
        return []

    async def collect_page(
        self,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[SearchItem], int]:
        rows = self.rows[offset : offset + limit]
        return rows, offset + len(rows)


class BackfillTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "search.db"
        self.provider = _PagedProvider()

    async def asyncTearDown(self) -> None:
        self.tmp.cleanup()

    async def test_backfill_resumes_from_persisted_cursor(self) -> None:
        first = await backfill_provider(
            self.provider,
            batch_size=2,
            batches=1,
            path=self.db,
        )
        self.assertEqual(first[0].active_after, 2)
        self.assertEqual(get_provider_state("paged", "backfill_cursor", path=self.db), "2")

        second = await backfill_provider(
            self.provider,
            batch_size=2,
            batches=2,
            path=self.db,
        )
        self.assertEqual(len(second), 2)
        self.assertEqual(count_items(self.db), 5)
        self.assertEqual(get_provider_state("paged", "backfill_cursor", path=self.db), "5")


    async def test_provider_backfill_cap_stops_automatic_crawl(self) -> None:
        self.provider.backfill_max_records = 3

        await backfill_provider(
            self.provider,
            batch_size=2,
            batches=3,
            path=self.db,
        )

        self.assertEqual(count_items(self.db), 3)
        self.assertEqual(
            get_provider_state("paged", "backfill_cursor", path=self.db),
            "3",
        )

    async def test_reset_restarts_cursor_without_losing_index(self) -> None:
        await backfill_provider(self.provider, batch_size=3, batches=1, path=self.db)
        await backfill_provider(
            self.provider,
            batch_size=2,
            batches=1,
            reset=True,
            path=self.db,
        )
        self.assertEqual(get_provider_state("paged", "backfill_cursor", path=self.db), "2")
        self.assertEqual(count_items(self.db), 3)


if __name__ == "__main__":
    unittest.main()
