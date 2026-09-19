from backend.live import HQPornLiveAdapter, parse_hqporn_listing

FIXTURE = '''
<div class="b-thumb-item js-thumb-item js-thumb">
  <div>
    <a class="js-gallery-stats js-gallery-link js-gallery-preview" href="/sample-video_123.html" data-preview="https://icdn05.hqporn.xxx/123/preview/sample.mp4" title="Sample &amp; Title">
      <img class="js-gallery-img" data-src="https://icdn05.hqporn.xxx/123/sample.jpg" alt="Sample &amp; Title">
      <div class="b-thumb-item__img-info"><div class="b-thumb-item__duration"><i class="icon-hd"></i><span>12:34</span></div></div>
    </a>
    <div class="b-thumb-item__title js-gallery-title">Sample &amp; Title</div>
  </div>
</div>
'''


def test_parse_hqporn_listing_core_metadata():
    rows = parse_hqporn_listing(FIXTURE, limit=5)
    assert len(rows) == 1
    item = rows[0]
    assert item.provider == "hqporn"
    assert str(item.url) == "https://hqporn.xxx/sample-video_123.html"
    assert item.title == "Sample & Title"
    assert str(item.thumbnail) == "https://icdn05.hqporn.xxx/123/sample.jpg"
    assert str(item.preview_url) == "https://icdn05.hqporn.xxx/123/preview/sample.mp4"
    assert item.duration_seconds == 754
    assert item.quality == "HD"


def test_hqporn_adapter_uses_public_search_pagination():
    class FixtureAdapter(HQPornLiveAdapter):
        def __init__(self):
            super().__init__()
            self.requested_url = ""

        def _fetch_text(self, url: str) -> str:
            self.requested_url = url
            return FIXTURE

    adapter = FixtureAdapter()
    result = adapter._search_sync("sample query", page=2, limit=1)
    assert adapter.requested_url == "https://hqporn.xxx/search/sample%20query/2/"
    assert result.page == 2
    assert len(result.items) == 1
