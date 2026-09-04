from __future__ import annotations

import unittest

from backend.live import parse_thumbzilla_listing


class ThumbzillaLiveParserTests(unittest.TestCase):
    def test_current_article_markup_is_parsed(self):
        raw = '''
        <article class="video-box pc js_video-box" aria-label="Sample clip">
          <a href="/watch/213296491/" class="video-box-image">
            <div>
              <img data-src="https://cdn.example/thumb.jpg"
                   data-poster="https://cdn.example/poster.jpg"
                   data-mediabook="https://cdn.example/preview.mp4">
            </div>
            <div class="video-duration"><span>11:30</span></div>
          </a>
        </article>
        '''
        rows = parse_thumbzilla_listing(raw, limit=5)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.provider, "thumbzilla")
        self.assertEqual(str(row.url), "https://www.thumbzilla.com/watch/213296491/")
        self.assertEqual(row.title, "Sample clip")
        self.assertEqual(str(row.thumbnail), "https://cdn.example/thumb.jpg")
        self.assertEqual(str(row.preview_url), "https://cdn.example/preview.mp4")
        self.assertEqual(row.duration_seconds, 690)


if __name__ == "__main__":
    unittest.main()
