from backend.live import BustyBusLiveAdapter, parse_bustybus_listing


FIXTURE = '''
<div class="b-thumb-item js-thumb-item js-thumb">
  <div>
    <a class="js-gallery-stats js-gallery-link" href="/video?play=12345" data-position="1" data-preview="" title="Sample &amp; Title">
      <div class="b-thumb-item__img js-gallery-preview">
        <picture class="js-gallery-img">
          <source type="image/webp" srcset="https://icdn05.bustybus.com/1/sample.webp">
          <img loading="lazy" data-src="https://icdn05.bustybus.com/1/sample.jpg" alt="Sample &amp; Title">
        </picture>
        <div class="b-thumb-item__img-info">
          <div class="clearfix"><div class="f-right b-thumb-item__duration"><span>01:04:08</span></div></div>
        </div>
      </div>
    </a>
    <div class="b-thumb-item__title js-gallery-title">Sample &amp; Title</div>
  </div>
</div>
'''


def test_parse_bustybus_listing_core_metadata():
    rows = parse_bustybus_listing(FIXTURE, limit=5)
    assert len(rows) == 1
    item = rows[0]
    assert item.provider == "bustybus"
    assert str(item.url) == "https://bustybus.com/video?play=12345"
    assert item.title == "Sample & Title"
    assert str(item.thumbnail) == "https://icdn05.bustybus.com/1/sample.jpg"
    assert item.preview_url is None
    assert item.duration_seconds == 3848


def test_bustybus_adapter_uses_public_search_pagination():
    class FixtureAdapter(BustyBusLiveAdapter):
        def __init__(self):
            super().__init__()
            self.requested_url = ""

        def _fetch_text(self, url: str) -> str:
            self.requested_url = url
            return FIXTURE

    adapter = FixtureAdapter()
    result = adapter._search_sync("sample query", page=2, limit=1)
    assert adapter.requested_url == "https://bustybus.com/search/sample%20query/2/"
    assert result.page == 2
    assert len(result.items) == 1
