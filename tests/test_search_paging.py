from __future__ import annotations

import unittest

from backend.models import SearchItem
from backend.search import _collapse, _slice_page


def item(item_id: str, title: str, duration: int = 60) -> SearchItem:
    return SearchItem(
        id=item_id,
        provider="sample",
        title=title,
        url=f"https://example.com/{item_id}",
        duration_seconds=duration,
        quality="1080p",
        score=1.0,
    )


class SearchPagingTests(unittest.TestCase):
    def test_slice_page_reports_more_results(self) -> None:
        rows = [item(str(index), f"Item {index}") for index in range(5)]

        page, has_more = _slice_page(rows, offset=2, limit=2)

        self.assertEqual([row.id for row in page], ["2", "3"])
        self.assertTrue(has_more)

    def test_last_page_has_no_more_results(self) -> None:
        rows = [item(str(index), f"Item {index}") for index in range(5)]

        page, has_more = _slice_page(rows, offset=4, limit=2)

        self.assertEqual([row.id for row in page], ["4"])
        self.assertFalse(has_more)

    def test_duplicates_are_collapsed_before_page_slice(self) -> None:
        rows = [
            item("a1", "Same title", 120),
            item("a2", "Same title", 121),
            item("b", "Different title", 90),
        ]

        collapsed = _collapse(rows, 10)
        page, has_more = _slice_page(collapsed, offset=0, limit=2)

        self.assertEqual(len(collapsed), 2)
        self.assertEqual(len(page), 2)
        self.assertFalse(has_more)
        self.assertEqual(len(page[0].alternate_sources), 1)


if __name__ == "__main__":
    unittest.main()
