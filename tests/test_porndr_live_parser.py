from backend.live import PornDrLiveAdapter, parse_porndr_listing


FIXTURE = '''
<div id="list_videos_videos_list_search_result_items">
  <div class="thumbs-wrap">
    <div class="item  ">
      <a class="intrsttl" href="https://www.porndr.com/videos/18470/sample-video/" title="Sample &amp; Title">
        <div class="img">
          <img class="thumb lazy-load"
               data-original="https://www.porndr.com/contents/videos_screenshots/18000/18470/320x180/1.jpg"
               alt="Sample &amp; Title"
               data-preview="https://www.porndr.com/get_file/1/token/18000/18470/18470_preview.mp4/" />
          <div class="bottom-info"><div class="wrap"><div class="duration">8:59</div></div></div>
        </div>
        <strong class="title">Sample &amp; Title</strong>
      </a>
    </div>
  </div>
</div>
<div class="pagination" id="list_videos_videos_list_search_result_pagination"></div>
'''


def test_parse_porndr_listing_core_metadata():
    rows = parse_porndr_listing(FIXTURE, limit=5)
    assert len(rows) == 1
    item = rows[0]
    assert item.provider == "porndr"
    assert str(item.url) == "https://www.porndr.com/videos/18470/sample-video/"
    assert item.title == "Sample & Title"
    assert str(item.thumbnail).endswith("/18000/18470/320x180/1.jpg")
    assert str(item.preview_url).endswith("/18470_preview.mp4/")
    assert item.duration_seconds == 539


def test_porndr_adapter_is_explicitly_page_one_only():
    class FixtureAdapter(PornDrLiveAdapter):
        def _fetch_text(self, url: str) -> str:
            raise AssertionError("page > 1 must not reverse-engineer private AJAX pagination")

    result = FixtureAdapter()._search_sync("sample query", page=2, limit=5)
    assert result.page == 2
    assert result.items == []
