from backend.live import AnyPornLiveAdapter, parse_anyporn_listing


def _fixture_html():
    return '''
    <div class='item  '>
      <div class="thmbclck"><div class="img"><div class="hdpng"></div>
        <a href='/1037106/'>
          <img class="thumb lazy-load"
               data-original="//static-ap3.cdnanp.com/videos_screenshots/1037000/1037106/240x180/4.jpg"
               alt="Sample &amp; Title"
               data-preview="https://anyporn.com/get_file/sample_preview.mp4/"
               src="/images/placeholder.png" />
        </a>
      </div>
      <a href='/1037106/'><strong class="title">Sample &amp; Title</strong></a>
      <div class="wrap"><div class="added"><em id="durationid_1037106">
        <script>var element=document.getElementById("durationid_1037106");element.innerHTML = "5m:56s";</script>
      </em></div></div>
    </div>
    '''


def test_parse_anyporn_listing_core_metadata():
    rows = parse_anyporn_listing(_fixture_html(), limit=5)
    assert len(rows) == 1
    item = rows[0]
    assert item.provider == "anyporn"
    assert str(item.url) == "https://anyporn.com/1037106/"
    assert item.title == "Sample & Title"
    assert str(item.thumbnail).startswith("https://static-ap3.cdnanp.com/")
    assert str(item.preview_url).endswith("sample_preview.mp4/")
    assert item.duration_seconds == 356
    assert item.quality == "HD"


def test_anyporn_adapter_is_explicitly_page_one_only():
    class FixtureAdapter(AnyPornLiveAdapter):
        def _fetch_text(self, url: str) -> str:
            raise AssertionError("page > 1 must not fetch an invented AJAX contract")

    result = FixtureAdapter()._search_sync("sample query", page=2, limit=5)
    assert result.page == 2
    assert result.items == []
