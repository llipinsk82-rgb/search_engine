from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.ingest import backfill_many
from backend.index import count_items, get_provider_state
from backend.models import SearchItem
from backend.providers.base import SearchProvider


class _PagedProvider(SearchProvider):
    sync_mode = "incremental"

    def __init__(
        self,
        name: str,
        total: int,
        *,
        fail: bool = False,
        priority: int = 100,
        batch_size: int | None = None,
        call_order: list[str] | None = None,
    ) -> None:
        self.name = name
        self.total = total
        self.fail = fail
        self.backfill_priority = priority
        self.backfill_batch_size = batch_size
        self.call_order = call_order
        self.offsets: list[int] = []

    async def search(self, query: str, limit: int = 40) -> list[SearchItem]:
        return []

    async def collect_page(self, *, offset: int, limit: int):
        if self.fail:
            raise RuntimeError("provider failed")
        self.offsets.append(offset)
        if self.call_order is not None:
            self.call_order.append(self.name)
        end = min(self.total, offset + limit)
        items = [
            SearchItem(
                id=f"{self.name}-{idx}",
                provider=self.name,
                title=f"Item {idx}",
                url=f"https://example.invalid/{self.name}/{idx}",
                thumbnail=None,
                duration_seconds=None,
                quality=None,
                tags=[],
                score=1.0,
            )
            for idx in range(offset, end)
        ]
        return items, end


class BackfillManyTests(unittest.IsolatedAsyncioTestCase):
    async def test_round_robin_backfill_advances_independent_cursors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "index.db"
            alpha = _PagedProvider("alpha", 5)
            beta = _PagedProvider("beta", 5)

            runs = await backfill_many(
                [alpha, beta],
                batch_size=2,
                batches_per_provider=2,
                path=db,
            )

            self.assertEqual(alpha.offsets, [0, 2])
            self.assertEqual(beta.offsets, [0, 2])
            self.assertEqual(count_items(db), 8)
            self.assertEqual(get_provider_state("alpha", "backfill_cursor", path=db), "4")
            self.assertEqual(get_provider_state("beta", "backfill_cursor", path=db), "4")
            self.assertEqual([run.fetched for run in runs], [4, 4])


    async def test_provider_priority_and_batch_size_override_global_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "index.db"
            order: list[str] = []
            slow = _PagedProvider(
                "slow",
                10,
                priority=20,
                batch_size=1,
                call_order=order,
            )
            fast = _PagedProvider(
                "fast",
                10,
                priority=10,
                batch_size=4,
                call_order=order,
            )

            runs = await backfill_many(
                [slow, fast],
                batch_size=2,
                batches_per_provider=1,
                path=db,
            )

            self.assertEqual(order, ["fast", "slow"])
            by_name = {run.provider: run for run in runs}
            self.assertEqual(by_name["fast"].fetched, 4)
            self.assertEqual(by_name["slow"].fetched, 1)
            self.assertEqual(
                get_provider_state("fast", "backfill_cursor", path=db),
                "4",
            )
            self.assertEqual(
                get_provider_state("slow", "backfill_cursor", path=db),
                "1",
            )

    async def test_failure_is_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "index.db"
            broken = _PagedProvider("broken", 4, fail=True)
            healthy = _PagedProvider("healthy", 4)

            runs = await backfill_many(
                [broken, healthy],
                batch_size=2,
                batches_per_provider=1,
                path=db,
            )

            by_name = {run.provider: run for run in runs}
            self.assertEqual(by_name["broken"].error, "provider failed")
            self.assertEqual(by_name["healthy"].fetched, 2)
            self.assertEqual(count_items(db), 2)

    async def test_zero_time_budget_does_not_start_network_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "index.db"
            provider = _PagedProvider("alpha", 4)
            with patch("backend.ingest.time.monotonic", side_effect=[10.0, 10.0]):
                runs = await backfill_many(
                    [provider],
                    batch_size=2,
                    batches_per_provider=2,
                    max_seconds=0,
                    path=db,
                )

            self.assertEqual(provider.offsets, [])
            self.assertEqual(runs[0].fetched, 0)
            self.assertEqual(count_items(db), 0)


if __name__ == "__main__":
    unittest.main()
