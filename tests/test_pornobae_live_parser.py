from backend.live import PornobaeLiveAdapter, parse_pornobae_listing

FIXTURE = '''
<article data-video-id="video_1" data-main-thumb="https://pornobae.com/wp-content/uploads/sample.jpg" class="loop-video thumb-block video-preview-item" data-post-id="123">
  <a href="https://pornobae.com/sample-video/" title="Sample &amp; Title">
    <div class="post-thumbnail">
      <div class="post-thumbnail-container"><img class="video-main-thumb" src="https://pornobae.com/wp-content/uploads/sample.jpg" alt="Sample &amp; Title"></div>
      <span class="duration"><i class="fa fa-clock-o"></i>12:34</span>
    </div>
  </a>
</article>
'''


def test_parse_pornobae_listing_core_metadata():
    rows = parse_pornobae_listing(FIXTURE, limit=5)
    assert len(rows) == 1
    item = rows[0]
    assert item.provider == "pornobae"
    assert str(item.url) == "https://pornobae.com/sample-video/"
    assert item.title == "Sample & Title"
    assert str(item.thumbnail) == "https://pornobae.com/wp-content/uploads/sample.jpg"
    assert item.preview_url is None
    assert item.duration_seconds == 754


def test_pornobae_adapter_uses_wordpress_search_pagination():
    class FixtureAdapter(PornobaeLiveAdapter):
        def __init__(self):
            super().__init__()
            self.requested_url = ""

        def _fetch_text(self, url: str) -> str:
            self.requested_url = url
            return FIXTURE

    adapter = FixtureAdapter()
    result = adapter._search_sync("sample query", page=2, limit=1)
    assert adapter.requested_url == "https://pornobae.com/page/2/?s=sample+query"
    assert result.page == 2
    assert len(result.items) == 1
