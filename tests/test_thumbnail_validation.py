from __future__ import annotations

import unittest

from backend.models import SearchItem


class ThumbnailValidationTests(unittest.TestCase):
    def _item(self, thumbnail: str) -> SearchItem:
        return SearchItem(
            id="one",
            provider="source",
            title="Example",
            url="https://example.com/watch/one",
            thumbnail=thumbnail,
        )

    def test_video_media_url_is_not_exposed_as_an_image(self) -> None:
        item = self._item("https://cdn.example.com/video.mp4/plain/frame?token=abc")
        self.assertIsNone(item.thumbnail)

    def test_signed_image_url_remains_available(self) -> None:
        item = self._item("https://cdn.example.com/thumb.jpg?token=abc")
        self.assertEqual(str(item.thumbnail), "https://cdn.example.com/thumb.jpg?token=abc")


if __name__ == "__main__":
    unittest.main()
