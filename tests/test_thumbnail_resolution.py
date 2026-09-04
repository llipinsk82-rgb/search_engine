from __future__ import annotations
import unittest
from unittest.mock import patch
from backend.models import SearchItem
from backend.providers.sitemap import SitemapProvider, needs_thumbnail_resolution

def make(provider="tube8", thumbnail="https://ei-ph.t8cdn.com/m=abc/videos/2024/01/1/original/1.jpg", url="https://www.tube8.com/porn-video/1/"):
    return SearchItem(id="x", provider=provider, title="X", url=url, thumbnail=thumbnail, tags=[])

class ThumbnailResolutionTests(unittest.TestCase):
    def test_legacy_tube8_needs_resolution(self):
        self.assertTrue(needs_thumbnail_resolution(make()))

    def test_modern_tube8_does_not_need_resolution(self):
        self.assertFalse(needs_thumbnail_resolution(make(thumbnail="https://ei-ph.t8cdn.com/abc/1.jpg?token=signed")))

    def test_other_provider_is_left_alone(self):
        self.assertFalse(needs_thumbnail_resolution(make(provider="xvideos", thumbnail="https://cdn.example/a.jpg", url="https://www.xvideos.com/video.1/a")))

    def test_off_origin_returns_original(self):
        p = SitemapProvider(name="tube8", sitemap_url="https://www.tube8.com/sitemap.xml", obey_robots=False)
        item = make(url="https://evil.example/video")
        original = str(item.thumbnail)
        self.assertEqual(p._resolve_thumbnail_sync(item), original)

    def test_force_resolution_can_update_thumbnail(self):
        p = SitemapProvider(name="tube8", sitemap_url="https://www.tube8.com/sitemap.xml", obey_robots=False)
        item = make(thumbnail="https://cdn.example/old.jpg")
        html = '<meta property="og:title" content="X"><meta property="og:image" content="https://cdn.example/new.jpg">'
        with patch.object(p, "_fetch_text", return_value=html):
            self.assertEqual(p._resolve_thumbnail_sync(item, force=True), "https://cdn.example/new.jpg")

if __name__ == "__main__":
    unittest.main()
