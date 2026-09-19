from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from backend.index import get_item, search_items, upsert_items
from backend.models import SearchItem


def test_sort_metadata_round_trips_through_sqlite(tmp_path: Path):
    db = tmp_path / "search.db"
    published = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    item = SearchItem(
        id="meta-1",
        provider="demo",
        title="Metadata item",
        url="https://example.com/meta-1",
        duration_seconds=321,
        published_at=published,
        views=123456,
        rating_percent=98.25,
        rating_count=777,
        tags=["sample"],
    )

    assert upsert_items([item], path=db) == 1

    direct = get_item("meta-1", path=db)
    assert direct is not None
    assert direct.published_at == published
    assert direct.views == 123456
    assert direct.rating_percent == 98.25
    assert direct.rating_count == 777

    rows = search_items("Metadata", path=db)
    assert len(rows) == 1
    assert rows[0].published_at == published
    assert rows[0].views == 123456
    assert rows[0].rating_percent == 98.25
    assert rows[0].rating_count == 777

    with sqlite3.connect(db) as conn:
        raw = conn.execute(
            "SELECT published_at, views, rating_percent, rating_count FROM items WHERE id='meta-1'"
        ).fetchone()
    assert raw == ("2026-01-02T03:04:05+00:00", 123456, 98.25, 777)
