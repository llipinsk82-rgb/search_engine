from backend.live import PornHatLiveAdapter, parse_pornhat_listing


FIXTURE = '''
<div class="item thumb-bl thumb-bl-video video_1">
  <div class="thumb thumb-video ">
    <a href="/video/sample-video/" title="Sample &amp; Title" data-preview-custom="https://www.pornhat.one/get_file/sample_preview360p.mp4/">
      <img class="thumb lazy-load" src="data:image/gif;base64,AAAA" data-original="https://static.pornhat.one/contents/videos_screenshots/sample/1.jpg" alt="Sample &amp; Title" />
    </a>
  </div>
  <div class="thumb-bl-info">
    <ul class="video-meta"><li><i class="fa fa-clock-o"></i> <span>12:34</span></li></ul>
  </div>
</div>
'''


def test_parse_pornhat_listing_core_metadata():
    rows = parse_pornhat_listing(FIXTURE, limit=5)
    assert len(rows) == 1
    item = rows[0]
    assert item.provider == "pornhat"
    assert str(item.url) == "https://www.pornhat.one/video/sample-video/"
    assert item.title == "Sample & Title"
    assert str(item.thumbnail) == "https://static.pornhat.one/contents/videos_screenshots/sample/1.jpg"
    assert str(item.preview_url) == "https://www.pornhat.one/get_file/sample_preview360p.mp4/"
    assert item.duration_seconds == 754
    assert item.quality is None


def test_pornhat_adapter_uses_search_path_and_pagination():
    class FixtureAdapter(PornHatLiveAdapter):
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
