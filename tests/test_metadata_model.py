from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.models import LiveRefreshRequest, SearchItem, SearchRequest


def make_item(**overrides):
    data = {
        "id": "x",
        "provider": "demo",
        "title": "X",
        "url": "https://example.com/x",
    }
    data.update(overrides)
    return SearchItem(**data)


def test_sort_metadata_is_optional_and_validated():
    item = make_item(
        published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        views=123,
        rating_percent=98.5,
        rating_count=42,
    )
    assert item.views == 123
    assert item.rating_percent == 98.5
    assert item.rating_count == 42
    assert SearchRequest(sort="views").sort == "views"
    assert LiveRefreshRequest(q="x", sort="newest").sort == "newest"


def test_sort_metadata_defaults_to_none_and_relevance():
    item = make_item()
    assert item.published_at is None
    assert item.views is None
    assert item.rating_percent is None
    assert item.rating_count is None
    assert SearchRequest().sort == "relevance"
    assert LiveRefreshRequest(q="x").sort == "relevance"


@pytest.mark.parametrize("field", ["views", "rating_count"])
def test_nonnegative_metadata_rejects_negative_values(field):
    with pytest.raises(ValidationError):
        make_item(**{field: -1})


@pytest.mark.parametrize("value", [-0.1, 100.1])
def test_rating_percent_rejects_out_of_range_values(value):
    with pytest.raises(ValidationError):
        make_item(rating_percent=value)


@pytest.mark.parametrize("value", [0.0, 100.0])
def test_rating_percent_accepts_boundaries(value):
    assert make_item(rating_percent=value).rating_percent == value


def test_invalid_sort_mode_is_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(sort="popular")
    with pytest.raises(ValidationError):
        LiveRefreshRequest(q="x", sort="popular")
