from datetime import datetime, timezone

import backend.live as live
from backend.models import SearchItem


def item(item_id, *, published_at=None, views=None, rating=None, votes=None, duration=None):
    return SearchItem(
        id=item_id,
        provider="demo",
        title=item_id,
        url=f"https://example.com/{item_id}",
        published_at=published_at,
        views=views,
        rating_percent=rating,
        rating_count=votes,
        duration_seconds=duration,
    )


def ids(items):
    return [entry.id for entry in items]


def test_live_relevance_preserves_provider_merge_order():
    rows = [item("a", views=2), item("b", views=100), item("c")]
    assert ids(live.sort_live_items(rows, "relevance")) == ["a", "b", "c"]


def test_live_non_relevance_sorts_known_before_missing_stably():
    rows = [
        item("missing-a"),
        item("low", published_at=datetime(2026, 1, 1, tzinfo=timezone.utc), views=10, rating=80, votes=2, duration=60),
        item("high-a", published_at=datetime(2026, 2, 1, tzinfo=timezone.utc), views=100, rating=99, votes=10, duration=120),
        item("high-b", published_at=datetime(2026, 2, 1, tzinfo=timezone.utc), views=100, rating=99, votes=10, duration=120),
        item("missing-b"),
    ]

    assert ids(live.sort_live_items(rows, "newest")) == ["high-a", "high-b", "low", "missing-a", "missing-b"]
    assert ids(live.sort_live_items(rows, "views")) == ["high-a", "high-b", "low", "missing-a", "missing-b"]
    assert ids(live.sort_live_items(rows, "rating")) == ["high-a", "high-b", "low", "missing-a", "missing-b"]
    assert ids(live.sort_live_items(rows, "longest")) == ["high-a", "high-b", "low", "missing-a", "missing-b"]
    assert ids(live.sort_live_items(rows, "shortest")) == ["low", "high-a", "high-b", "missing-a", "missing-b"]


def test_live_refresh_sorts_only_the_merged_fetched_batch():
    import asyncio
    from unittest.mock import AsyncMock, patch
    from fastapi import BackgroundTasks
    from backend.app import live_refresh
    from backend.live import LiveProviderResult, LiveRefreshResult
    from backend.models import LiveRefreshRequest

    result = LiveRefreshResult(
        providers=[
            LiveProviderResult("p1", [item("low", views=10), item("missing")], None, 1, 1),
            LiveProviderResult("p2", [item("high", views=100)], None, 1, 1),
        ],
        cached_items=0,
    )
    with (
        patch("backend.app.refresh_live_search", AsyncMock(return_value=result)),
        patch("backend.app.count_items", return_value=3),
    ):
        response = asyncio.run(
            live_refresh(LiveRefreshRequest(q="alpha", sort="views"), BackgroundTasks())
        )

    assert ids(response.items) == ["high", "low", "missing"]
