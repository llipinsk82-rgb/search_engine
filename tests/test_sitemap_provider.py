from __future__ import annotations

import unittest

from backend.providers.sitemap import parse_video_metadata


class VideoMetadataParserTests(unittest.TestCase):
    def test_parses_videoobject_metadata(self) -> None:
        html = """
        <html>
          <head>
            <meta charset="utf-8">
            <meta property="video:height" content="1080">
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "VideoObject",
              "name": "Sample Video",
              "thumbnailUrl": "/thumb.jpg",
              "duration": "PT1H2M3S",
              "keywords": ["alpha", "beta"]
            }
            </script>
          </head>
        </html>
        """

        item = parse_video_metadata(
            html,
            provider="sample",
            page_url="https://example.com/watch/1",
        )

        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.provider, "sample")
        self.assertEqual(item.title, "Sample Video")
        self.assertEqual(item.duration_seconds, 3723)
        self.assertEqual(item.quality, "1080p")
        self.assertEqual(item.tags, ["alpha", "beta"])
        self.assertEqual(str(item.thumbnail), "https://example.com/thumb.jpg")

    def test_falls_back_to_open_graph_metadata(self) -> None:
        html = """
        <html>
          <head>
            <meta property="og:title" content="Open Graph Video">
            <meta property="og:image" content="https://cdn.example.com/preview.jpg">
            <meta property="og:duration" content="95">
            <meta property="og:video:height" content="2160">
            <meta name="keywords" content="one, two; three">
          </head>
        </html>
        """

        item = parse_video_metadata(
            html,
            provider="sample",
            page_url="https://example.com/watch/2",
        )

        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.title, "Open Graph Video")
        self.assertEqual(item.duration_seconds, 95)
        self.assertEqual(item.quality, "4K")
        self.assertEqual(item.tags, ["one", "two", "three"])

    def test_page_without_title_is_ignored(self) -> None:
        item = parse_video_metadata(
            "<html><head></head><body></body></html>",
            provider="sample",
            page_url="https://example.com/watch/3",
        )
        self.assertIsNone(item)


if __name__ == "__main__":
    unittest.main()
