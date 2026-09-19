from backend.live import RedTubeLiveAdapter, parse_redtube_video


def _fixture_video():
    return {
        "video": {
            "video_id": "123456",
            "title": "Sample &amp; Title",
            "url": "https://www.redtube.com/123456",
            "thumb": "https://ei-ph.rdtcdn.com/videos/example.jpg",
            "default_thumb": "https://ei-ph.rdtcdn.com/videos/example.jpg",
            "duration": "38:44",
            "tags": [{"tag_name": "alpha"}, {"tag_name": "beta"}],
        }
    }


def test_parse_redtube_video_core_metadata():
    item = parse_redtube_video(_fixture_video())
    assert item is not None
    assert item.provider == "redtube"
    assert item.title == "Sample & Title"
    assert str(item.url) == "https://www.redtube.com/123456"
    assert str(item.thumbnail) == "https://ei-ph.rdtcdn.com/videos/example.jpg"
    assert item.duration_seconds == 2324
    assert item.tags == ["alpha", "beta"]
    assert item.preview_url is None
    assert item.quality is None


def test_redtube_adapter_uses_api_pagination_and_count():
    class FixtureAdapter(RedTubeLiveAdapter):
        def __init__(self):
            super().__init__()
            self.requested_url = ""

        def _fetch_json(self, url: str):
            self.requested_url = url
            return {"count": 42, "videos": [_fixture_video()]}

    adapter = FixtureAdapter()
    result = adapter._search_sync("sample query", page=2, limit=1)
    assert "search=sample+query" in adapter.requested_url
    assert "page=2" in adapter.requested_url
    assert result.total == 42
    assert result.page == 2
    assert len(result.items) == 1
