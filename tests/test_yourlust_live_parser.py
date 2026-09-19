from backend.live import YourLustLiveAdapter, parse_yourlust_listing

FIXTURE = '''
<div class="list_videos">
  <div class="block_content">
    <div class="item">
      <div class="image">
        <a href="/videos/sample-video.html" title="Sample &amp; Title" class="hl popfire">
          <img class="thumb" src="https://i.yourlust.com/videos_screenshots/1/240x180/1.jpg" alt="Sample &amp; Title" />
        </a>
      </div>
      <div class="info">
        <div class="length">12:34</div>
      </div>
    </div>
  </div>
  <div class="pagination"></div>
</div>
'''


def test_parse_yourlust_listing_core_metadata():
    rows = parse_yourlust_listing(FIXTURE, limit=5)
    assert len(rows) == 1
    item = rows[0]
    assert item.provider == "yourlust"
    assert str(item.url) == "https://yourlust.com/videos/sample-video.html"
    assert item.title == "Sample & Title"
    assert str(item.thumbnail) == "https://i.yourlust.com/videos_screenshots/1/240x180/1.jpg"
    assert item.preview_url is None
    assert item.duration_seconds == 754


def test_yourlust_adapter_uses_public_search_pagination():
    class FixtureAdapter(YourLustLiveAdapter):
        def __init__(self):
            super().__init__()
            self.requested_url = ""

        def _fetch_text(self, url: str) -> str:
            self.requested_url = url
            return FIXTURE

    adapter = FixtureAdapter()
    result = adapter._search_sync("sample query", page=2, limit=1)
    assert adapter.requested_url == "https://yourlust.com/search/2/?q=sample+query"
    assert result.page == 2
    assert len(result.items) == 1
