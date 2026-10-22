from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.index import replace_provider_items, search_items
from backend.models import SearchItem


def make_item(item_id: str, title: str, tags: list[str]) -> SearchItem:
    return SearchItem(
        id=item_id,
        provider="rank",
        title=title,
        url=f"https://example.com/{item_id}",
        duration_seconds=120,
        quality="1080p",
        tags=tags,
    )


class SearchRankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "search.db"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_title_match_ranks_above_tag_only_match(self) -> None:
        replace_provider_items(
            "rank",
            [
                make_item("tag", "Unrelated title", ["alpha"]),
                make_item("title", "Alpha exact title", ["other"]),
            ],
            path=self.db,
        )

        rows = search_items("alpha", path=self.db)

        self.assertEqual([row.id for row in rows[:2]], ["title", "tag"])
        self.assertGreater(rows[0].score, rows[1].score)

    def test_space_and_plus_queries_require_every_word(self) -> None:
        replace_provider_items(
            "rank",
            [
                make_item("all-title", "sis step family", []),
                make_item("split", "sis step", ["family"]),
                make_item("missing", "sis family", []),
            ],
            path=self.db,
        )

        expected = {"all-title", "split"}
        self.assertEqual({row.id for row in search_items("sis step family", path=self.db)}, expected)
        self.assertEqual({row.id for row in search_items("sis+step+family", path=self.db)}, expected)


if __name__ == "__main__":
    unittest.main()
