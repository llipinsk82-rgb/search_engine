from backend.live import MILFPornLiveAdapter, parse_milfporn_listing

FIXTURE = '''
<div class="sybil" data-millicent="10528293"><a href="/videos/10528293-elegant-brad-newman-and-johnny-love-at-family-stokes-video.html" target="_self"><img class="jada" data-src="https://cdn.milfporn.tv/66/457/10528293/1_460.jpg" /></a><div class="bonnie">44:20</div></div>
<div class="sybil" data-millicent="82627406"><a href="https://www.latestpornvideos.com/videos/external.html" rel="nofollow" target="_self"><img class="jada" data-src="https://cdn.milfporn.tv/1/068/82627406/1_460.jpg" /></a><div class="bonnie">28:52</div></div>
'''


def test_parse_milfporn_listing_keeps_only_local_complete_cards():
    rows = parse_milfporn_listing(FIXTURE, limit=5)
    assert len(rows) == 1
    item = rows[0]
    assert item.provider == "milfporn"
    assert str(item.url) == "https://www.milfporn.tv/videos/10528293-elegant-brad-newman-and-johnny-love-at-family-stokes-video.html"
    assert item.title == "Elegant Brad Newman And Johnny Love At Family Stokes Video"
    assert str(item.thumbnail) == "https://cdn.milfporn.tv/66/457/10528293/1_460.jpg"
    assert item.preview_url is None
    assert item.duration_seconds == 2660


def test_milfporn_adapter_uses_public_search_pagination():
    class FixtureAdapter(MILFPornLiveAdapter):
        def __init__(self):
            super().__init__()
            self.requested_url = ""

        def _fetch_text(self, url: str) -> str:
            self.requested_url = url
            return FIXTURE

    adapter = FixtureAdapter()
    result = adapter._search_sync("Sample Query", page=2, limit=1)
    assert adapter.requested_url == "https://www.milfporn.tv/search/sample-query/2/"
    assert result.page == 2
    assert len(result.items) == 1
