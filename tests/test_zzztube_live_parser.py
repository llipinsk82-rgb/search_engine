from backend.live import ZZZTubeLiveAdapter, parse_zzztube_listing


FIXTURE = '''
<div class="b-thumb-item js-thumb">
  <div class="b-thumb-item__img js-gallery-preview">
    <a class="js-gallery-link" href="/551801?title=sample-title" title="Sample &amp; Title" data-preview="">
      <picture>
        <source srcset="https://icdn05.zzztube.com/40031/2001533_1.webp" type="image/webp">
        <img data-src="https://icdn05.zzztube.com/40031/2001533_1.jpg" alt="Sample &amp; Title">
      </picture>
      <div class="b-thumb-item__img-info">
        <div class="clearfix"><div class="f-right b-thumb-item__duration"><i class="icon-hd"></i><span>35:51</span></div></div>
      </div>
    </a>
  </div>
  <div class="b-thumb-item__title js-gallery-title">Sample &amp; Title</div>
</div>
'''


def test_parse_zzztube_listing_core_metadata():
    rows = parse_zzztube_listing(FIXTURE, limit=5)
    assert len(rows) == 1
    item = rows[0]
    assert item.provider == "zzztube"
    assert str(item.url) == "https://zzztube.com/551801?title=sample-title"
    assert item.title == "Sample & Title"
    assert str(item.thumbnail) == "https://icdn05.zzztube.com/40031/2001533_1.jpg"
    assert item.preview_url is None
    assert item.duration_seconds == 2151
    assert item.quality == "HD"


def test_zzztube_adapter_uses_search_path_and_pagination():
    class FixtureAdapter(ZZZTubeLiveAdapter):
        def __init__(self):
            super().__init__()
            self.requested_url = ""

        def _fetch_text(self, url: str) -> str:
            self.requested_url = url
            return FIXTURE

    adapter = FixtureAdapter()
    result = adapter._search_sync("sample query", page=2, limit=1)
    assert adapter.requested_url.endswith("/search/sample%20query/2/")
    assert result.page == 2
    assert len(result.items) == 1
