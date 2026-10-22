from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from backend.models import SearchItem
from backend.providers.demo import DemoProvider
from backend.providers.sitemap import SitemapProvider


class LiveSearchTermTests(unittest.IsolatedAsyncioTestCase):
    async def test_demo_requires_all_terms_in_any_order_for_space_or_plus(self) -> None:
        provider = DemoProvider()
        for query in ("sample studio", "sample+studio"):
            rows = await provider.search(query)
            self.assertEqual(len(rows), 2)
            self.assertTrue(all("Studio Sample" in row.title for row in rows))

    async def test_sitemap_matches_terms_across_title_and_tags(self) -> None:
        provider = SitemapProvider(name="fixture", sitemap_url="https://example.com/sitemap.xml")
        provider.collect = AsyncMock(return_value=[
            SearchItem(
                id="all", provider="fixture", title="sis step", url="https://example.com/all", tags=["family"]
            ),
            SearchItem(
                id="missing", provider="fixture", title="sis family", url="https://example.com/missing"
            ),
        ])

        for query in ("sis step family", "sis+step+family"):
            self.assertEqual([row.id for row in await provider.search(query)], ["all"])


if __name__ == "__main__":
    unittest.main()
