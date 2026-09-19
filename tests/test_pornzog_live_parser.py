from backend.live import PornZogLiveAdapter, parse_pornzog_listing


FIXTURE = '''
<ul class="thumbs-list thumbs-videos-list">
  <li>
    <div class="thumb-video lol2" data-percent="77">
      <div class="thumb-video-left"><div class="thumb-container">
        <a class="thumb-video-link test3" href="/video/9836930/sample-video/" target="_blank">
          <img class="thumb" src="data:image/gif;base64,AAAA"
               data-original="https://tn1.pornzog.com/media/videos/tmb/009/836/930/2.jpg"
               alt="Sample &amp; Title" />
          <div class="overlay"></div>
          <div class="duration">30:52</div>
          <div class="hd">hd</div>
        </a>
      </div></div>
      <div class="thumb-data">
        <a class="title" href="/video/9836930/sample-video/" target="_blank"><span>Sample &amp; Title</span></a>
        <p class="tags"><a href="/search/?s=sample">sample</a>, <a href="/search/?s=tag">tag</a></p>
      </div>
    </div>
  </li>
</ul>
'''


def test_parse_pornzog_listing_core_metadata():
    rows = parse_pornzog_listing(FIXTURE, limit=5)
    assert len(rows) == 1
    item = rows[0]
    assert item.provider == "pornzog"
    assert str(item.url) == "https://pornzog.com/video/9836930/sample-video/"
    assert item.title == "Sample & Title"
    assert str(item.thumbnail) == "https://tn1.pornzog.com/media/videos/tmb/009/836/930/2.jpg"
    assert item.preview_url is None
    assert item.duration_seconds == 1852
    assert item.quality == "HD"
    assert item.tags == ["sample", "tag"]


def test_pornzog_adapter_uses_public_get_search_and_page_query():
    class FixtureAdapter(PornZogLiveAdapter):
        def __init__(self):
            super().__init__()
            self.requested_url = ""

        def _fetch_text(self, url: str) -> str:
            self.requested_url = url
            return FIXTURE

    adapter = FixtureAdapter()
    result = adapter._search_sync("sample query", page=2, limit=1)
    assert adapter.requested_url == "https://pornzog.com/search/?s=sample%20query&page=2"
    assert result.page == 2
    assert len(result.items) == 1
