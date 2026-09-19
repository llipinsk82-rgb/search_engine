from datetime import datetime, timezone
from pathlib import Path

from backend.index import replace_provider_items, search_items
from backend.models import SearchItem


def item(
    item_id: str,
    *,
    published_at=None,
    views=None,
    rating_percent=None,
    rating_count=None,
    duration_seconds=None,
):
    return SearchItem(
        id=item_id,
        provider="sort",
        title=f"Sort {item_id}",
        url=f"https://example.com/{item_id}",
        published_at=published_at,
        views=views,
        rating_percent=rating_percent,
        rating_count=rating_count,
        duration_seconds=duration_seconds,
        tags=["sort"],
    )


def ids(rows):
    return [row.id for row in rows]


def seed(db: Path):
    replace_provider_items(
        "sort",
        [
            item(
                "newer",
                published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
                views=10,
                rating_percent=80,
                rating_count=50,
                duration_seconds=120,
            ),
            item(
                "older",
                published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                views=1000,
                rating_percent=99,
                rating_count=10,
                duration_seconds=300,
            ),
            item(
                "rated_more",
                published_at=datetime(2025, 12, 1, tzinfo=timezone.utc),
                views=100,
                rating_percent=99,
                rating_count=100,
                duration_seconds=60,
            ),
            item("missing"),
        ],
        path=db,
    )


def test_non_relevance_sort_modes_put_missing_metadata_last(tmp_path: Path):
    db = tmp_path / "search.db"
    seed(db)

    assert ids(search_items("", sort="newest", path=db)) == ["newer", "older", "rated_more", "missing"]
    assert ids(search_items("", sort="views", path=db)) == ["older", "rated_more", "newer", "missing"]
    assert ids(search_items("", sort="rating", path=db)) == ["rated_more", "older", "newer", "missing"]
    assert ids(search_items("", sort="longest", path=db)) == ["older", "newer", "rated_more", "missing"]
    assert ids(search_items("", sort="shortest", path=db)) == ["rated_more", "newer", "older", "missing"]


def test_sorted_pagination_uses_global_sql_order(tmp_path: Path):
    db = tmp_path / "search.db"
    seed(db)

    first = search_items("", sort="views", offset=0, limit=2, path=db)
    second = search_items("", sort="views", offset=2, limit=2, path=db)

    assert ids(first) == ["older", "rated_more"]
    assert ids(second) == ["newer", "missing"]


def test_relevance_sort_remains_default_and_explicit(tmp_path: Path):
    db = tmp_path / "search.db"
    replace_provider_items(
        "sort",
        [
            SearchItem(id="tag", provider="sort", title="Other", url="https://example.com/tag", tags=["alpha"]),
            SearchItem(id="title", provider="sort", title="Alpha title", url="https://example.com/title", tags=["other"]),
        ],
        path=db,
    )

    assert ids(search_items("alpha", path=db)) == ids(search_items("alpha", sort="relevance", path=db))
    assert ids(search_items("alpha", sort="relevance", path=db))[:2] == ["title", "tag"]
