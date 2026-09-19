from backend.live import BigFuckLiveAdapter, parse_bigfuck_listing


FIXTURE = '''
<div class="b-thumb-item js-thumb-item">
  <div class="b-thumb-item__inner">
    <a class="js-gallery-stats js-gallery-link js-gallery-preview" href="/video/12345/sample-video/" data-position="1" data-preview="https://icdn05.bigfuck.tv/1/preview/sample.mp4">
      <img class="js-gallery-img" src="https://dicdn.bigfuck.tv/sample.webp" alt="Sample &amp; Title">
      <div class="thumb-badge left"><span class="b-thumb-item__hd">HD</span> 07:45 </div>
    </a>
    <h3 class="b-thumb-item__title js-gallery-title">Sample &amp; Title</h3>
  </div>
</div>
'''


def test_parse_bigfuck_listing_core_metadata():
    rows = parse_bigfuck_listing(FIXTURE, limit=5)
    assert len(rows) == 1
    item = rows[0]
    assert item.provider == "bigfuck"
    assert str(item.url) == "https://bigfuck.tv/video/12345/sample-video/"
    assert item.title == "Sample & Title"
    assert str(item.thumbnail) == "https://dicdn.bigfuck.tv/sample.webp"
    assert str(item.preview_url) == "https://icdn05.bigfuck.tv/1/preview/sample.mp4"
    assert item.duration_seconds == 465
    assert item.quality == "HD"


def test_bigfuck_adapter_uses_public_search_pagination():
    class FixtureAdapter(BigFuckLiveAdapter):
        def __init__(self):
            super().__init__()
            self.requested_url = ""

        def _fetch_text(self, url: str) -> str:
            self.requested_url = url
            return FIXTURE

    adapter = FixtureAdapter()
    result = adapter._search_sync("sample query", page=2, limit=1)
    assert adapter.requested_url == "https://bigfuck.tv/s/sample%20query/2/"
    assert result.page == 2
    assert len(result.items) == 1
