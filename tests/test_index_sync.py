from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.index import (
    count_items,
    deactivate_provider,
    merge_provider_items,
    replace_provider_items,
    search_items,
)
from backend.models import SearchItem


def item(item_id: str, title: str, *, provider: str = "demo") -> SearchItem:
    return SearchItem(
        id=item_id,
        provider=provider,
        title=title,
        url=f"https://example.com/{item_id}",
        duration_seconds=600,
        quality="1080p",
        tags=["sample"],
    )


class ProviderSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "search.db"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_replaces_snapshot_and_removes_stale_fts_entries(self) -> None:
        first = [item("a", "Alpha One"), item("b", "Beta Old")]
        replace_provider_items("demo", first, path=self.db)

        result = replace_provider_items(
            "demo",
            [item("a", "Alpha Updated"), item("c", "Gamma New")],
            path=self.db,
        )

        self.assertEqual(result.active_before, 2)
        self.assertEqual(result.active_after, 2)
        self.assertEqual(result.deactivated, 1)
        self.assertEqual(count_items(self.db), 2)
        self.assertEqual(search_items("Beta", path=self.db), [])
        self.assertEqual([row.id for row in search_items("Gamma", path=self.db)], ["c"])

    def test_empty_sync_is_rejected_and_preserves_index(self) -> None:
        replace_provider_items("demo", [item("a", "Alpha")], path=self.db)

        with self.assertRaises(ValueError):
            replace_provider_items("demo", [], path=self.db)

        self.assertEqual(count_items(self.db), 1)
        self.assertEqual([row.id for row in search_items("Alpha", path=self.db)], ["a"])

    def test_explicit_empty_sync_can_deactivate_provider(self) -> None:
        replace_provider_items("demo", [item("a", "Alpha")], path=self.db)

        result = replace_provider_items(
            "demo",
            [],
            allow_empty=True,
            path=self.db,
        )

        self.assertEqual(result.deactivated, 1)
        self.assertEqual(result.active_after, 0)
        self.assertEqual(count_items(self.db), 0)

    def test_incremental_merge_keeps_older_provider_items(self) -> None:
        replace_provider_items(
            "demo",
            [item("old", "Older item")],
            path=self.db,
        )

        result = merge_provider_items(
            "demo",
            [item("new", "New item")],
            path=self.db,
        )

        self.assertEqual(result.active_before, 1)
        self.assertEqual(result.active_after, 2)
        self.assertEqual(result.deactivated, 0)
        self.assertEqual(
            {row.id for row in search_items("", path=self.db)},
            {"old", "new"},
        )

    def test_deactivate_provider_removes_it_from_search(self) -> None:
        replace_provider_items("demo", [item("a", "Alpha")], path=self.db)

        removed = deactivate_provider("demo", path=self.db)

        self.assertEqual(removed, 1)
        self.assertEqual(count_items(self.db), 0)
        self.assertEqual(search_items("Alpha", path=self.db), [])

    def test_empty_query_preserves_provider_snapshot_order(self) -> None:
        replace_provider_items(
            "demo",
            [
                item("newest", "Newest"),
                item("middle", "Middle"),
                item("oldest", "Oldest"),
            ],
            path=self.db,
        )

        rows = search_items("", path=self.db)

        self.assertEqual(
            [row.id for row in rows[:3]],
            ["newest", "middle", "oldest"],
        )

    def test_provider_mismatch_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            replace_provider_items(
                "demo",
                [item("a", "Alpha", provider="other")],
                path=self.db,
            )


if __name__ == "__main__":
    unittest.main()
